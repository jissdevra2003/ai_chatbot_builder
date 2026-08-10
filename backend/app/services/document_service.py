import os
from typing import List, Optional
from fastapi import HTTPException, UploadFile, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.base import generate_uuid
from app.models.document import Document, DocumentChunk, DocumentStatusEnum
from app.models.chatbot import Chatbot
from app.services.chunking import parse_file, chunk_text, SUPPORTED_FILE_TYPES
from app.services.vector_service import VectorService
from app.services.ai_service import AIService


class DocumentService:
    @classmethod
    def _get_upload_dir(cls, org_id: str, chatbot_id: str) -> str:
        """Returns the file upload directory path for an org/chatbot combo."""
        upload_dir = os.path.join(settings.UPLOAD_DIR, org_id, chatbot_id)
        os.makedirs(upload_dir, exist_ok=True)
        return upload_dir

    @classmethod
    def upload_document(
        cls,
        db: Session,
        org_id: str,
        chatbot_id: str,
        file: UploadFile,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Document:
        """
        Uploads a file, saves it to disk, and creates a Document record.
        Then schedules the processing pipeline (parse → chunk → embed) in background.
        """
        # 1. Validate file type
        filename = file.filename or "unknown"
        file_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if file_ext not in SUPPORTED_FILE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: '.{file_ext}'. Supported: {', '.join(SUPPORTED_FILE_TYPES)}"
            )

        # 2. Read file content and check size
        file_content = file.file.read()
        file_size = len(file_content)
        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size // (1024*1024)}MB) exceeds maximum ({settings.MAX_UPLOAD_SIZE_MB}MB)."
            )

        # 3. Save file to disk
        upload_dir = cls._get_upload_dir(org_id, chatbot_id)
        file_path = os.path.join(upload_dir, filename)

        # Handle duplicate filenames by appending a counter
        base_name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(file_path):
            file_path = os.path.join(upload_dir, f"{base_name}_{counter}{ext}")
            counter += 1

        with open(file_path, "wb") as f:
            f.write(file_content)

        # 4. Create Document record
        document = Document(
            chatbot_id=chatbot_id,
            org_id=org_id,
            filename=os.path.basename(file_path),
            file_type=file_ext,
            file_size_bytes=file_size,
            status=DocumentStatusEnum.PENDING,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        # 5. Trigger processing pipeline asynchronously
        if background_tasks:
            background_tasks.add_task(
                cls.process_document_background,
                document.id,
                file_path,
                chatbot_id
            )
        else:
            cls.process_document(db, document.id, file_path, chatbot_id)

        return document

    @classmethod
    def process_document_background(cls, document_id: str, file_path: str, chatbot_id: str) -> None:
        """Background task entry point that manages its own standalone database session."""
        db = SessionLocal()
        try:
            cls.process_document(db, document_id, file_path, chatbot_id)
        finally:
            db.close()

    @classmethod
    def process_document(cls, db: Session, document_id: str, file_path: str, chatbot_id: str) -> None:
        """
        Runs the full document processing pipeline:
        Parse → Chunk → Bulk DB Insert → Gemini Embeddings → Vector Store.
        """
        document = db.execute(select(Document).where(Document.id == document_id)).scalars().first()
        if not document:
            return

        # Get chatbot for chunking config
        chatbot = db.execute(select(Chatbot).where(Chatbot.id == chatbot_id)).scalars().first()
        chunk_size = chatbot.chunk_size if chatbot else settings.DEFAULT_CHUNK_SIZE
        chunk_overlap = chatbot.chunk_overlap if chatbot else settings.DEFAULT_CHUNK_OVERLAP

        # Mark as processing
        document.status = DocumentStatusEnum.PROCESSING
        db.commit()

        try:
            # 1. Parse file to text
            raw_text = parse_file(file_path, document.file_type)
            if not raw_text or not raw_text.strip():
                raise ValueError("No text content could be extracted from the file.")

            # 2. Chunk the text
            text_chunks = chunk_text(raw_text, chunk_size=chunk_size, overlap=chunk_overlap)
            if not text_chunks:
                raise ValueError("Text chunking produced zero chunks.")

            # 3. Build chunk objects with pre-generated UUIDs
            chunk_ids = []
            chunk_texts = []
            chunk_metadatas = []
            db_chunks = []

            for idx, chunk_content in enumerate(text_chunks):
                chunk_id = generate_uuid()
                db_chunk = DocumentChunk(
                    id=chunk_id,
                    document_id=document.id,
                    chunk_index=idx,
                    content=chunk_content,
                    char_count=len(chunk_content),
                    embedding_id=chunk_id,
                )
                db_chunks.append(db_chunk)
                chunk_ids.append(chunk_id)
                chunk_texts.append(chunk_content)
                chunk_metadatas.append({
                    "document_id": document.id,
                    "org_id": document.org_id,
                    "chatbot_id": chatbot_id,
                    "chunk_index": idx,
                    "filename": document.filename,
                })

            # 4. Bulk insert chunks to database
            db.add_all(db_chunks)
            db.flush()

            # 5. Generate embeddings using Gemini API
            embeddings = None
            try:
                embeddings = AIService.generate_embeddings(chunk_texts)
            except Exception as emb_err:
                print(f"Warning: Gemini embedding generation failed, falling back: {emb_err}")

            # 6. Add chunks & embeddings to ChromaDB vector store
            VectorService.add_chunks(
                chatbot_id=chatbot_id,
                chunk_ids=chunk_ids,
                chunk_texts=chunk_texts,
                metadatas=chunk_metadatas,
                embeddings=embeddings,
            )

            # 7. Mark document as completed
            document.chunk_count = len(text_chunks)
            document.status = DocumentStatusEnum.COMPLETED
            db.commit()

        except Exception as e:
            db.rollback()
            # Re-fetch document after rollback
            document = db.execute(select(Document).where(Document.id == document_id)).scalars().first()
            if document:
                document.status = DocumentStatusEnum.FAILED
                document.error_message = str(e)[:2000]
                db.commit()

    @classmethod
    def list_documents(cls, db: Session, org_id: str, chatbot_id: str) -> List[Document]:
        """Lists all documents for a chatbot, scoped by organization."""
        stmt = (
            select(Document)
            .where(Document.chatbot_id == chatbot_id, Document.org_id == org_id)
            .order_by(Document.created_at.desc())
        )
        return list(db.execute(stmt).scalars().all())

    @classmethod
    def get_document(cls, db: Session, org_id: str, document_id: str) -> Document:
        """Gets a single document by ID, scoped by organization."""
        stmt = select(Document).where(Document.id == document_id, Document.org_id == org_id)
        document = db.execute(stmt).scalars().first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found."
            )
        return document

    @classmethod
    def get_document_chunks(cls, db: Session, document_id: str) -> List[DocumentChunk]:
        """Gets all chunks for a document, ordered by chunk_index."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(db.execute(stmt).scalars().all())

    @classmethod
    def delete_document(cls, db: Session, org_id: str, chatbot_id: str, document_id: str) -> None:
        """Deletes a document, its chunks, and purges vectors from the store."""
        document = cls.get_document(db, org_id, document_id)

        # Remove vectors from ChromaDB
        VectorService.delete_document_vectors(chatbot_id, document_id)

        # Delete file from disk (best effort)
        try:
            upload_dir = cls._get_upload_dir(org_id, chatbot_id)
            file_path = os.path.join(upload_dir, document.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass

        # Delete from database (cascades to chunks)
        db.delete(document)
        db.commit()
