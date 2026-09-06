"""
Document Service — Lightweight orchestrator for document management.

ARCHITECTURE:
  Upload flow:
    1. Validate file (extension, MIME, size, empty)
    2. Sanitize filename, generate safe storage path
    3. Stream file to disk in 64KB chunks (bounded memory)
    4. Create Document DB record (status=QUEUED)
    5. Dispatch Celery task for background processing
    6. Return 201 immediately — server stays responsive

  The Celery worker does ALL heavy lifting (extract → chunk → embed → index)
  in its own process.  If the worker crashes, FastAPI stays alive.
  The frontend polls GET /documents/ for status updates.
"""
import os
import re
import logging
from typing import List, Optional
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.config import settings
from app.models.base import generate_uuid
from app.models.document import Document, DocumentChunk, DocumentStatusEnum, ACTIVE_STATUSES
from app.models.chatbot import Chatbot

logger = logging.getLogger(__name__)

# File upload constants
STREAM_READ_CHUNK_SIZE = 64 * 1024  # 64KB per disk-read iteration
SUPPORTED_FILE_TYPES = {"pdf", "docx", "txt", "csv"}

# MIME type mapping for validation
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/csv",
    "application/csv",
    "application/octet-stream",  # Fallback for some file types
}

# Map extensions to expected MIME types
EXTENSION_MIME_MAP = {
    "pdf": {"application/pdf"},
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"},
    "txt": {"text/plain", "application/octet-stream"},
    "csv": {"text/csv", "application/csv", "text/plain", "application/octet-stream"},
}


def _sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename for safe storage.
    Removes path separators, null bytes, and other dangerous characters.
    """
    # Remove path components
    filename = os.path.basename(filename)

    # Remove null bytes and control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)

    # Remove path traversal patterns
    filename = filename.replace('..', '_')

    # Replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext

    return filename or "unnamed_file"


def _detect_mime_type(file_path: str) -> Optional[str]:
    """Detects the MIME type of a file using python-magic."""
    try:
        import magic
        return magic.from_file(file_path, mime=True)
    except Exception as e:
        logger.warning(f"MIME detection failed: {e}")
        return None


class DocumentService:
    @classmethod
    def _get_storage_dir(cls, org_id: str) -> str:
        """Returns the storage directory for an organization's documents."""
        storage_dir = os.path.join(settings.UPLOAD_DIR, f"org_{org_id}")
        os.makedirs(storage_dir, exist_ok=True)
        return storage_dir

    @classmethod
    def upload_document(
        cls,
        db: Session,
        org_id: str,
        chatbot_id: str,
        file: UploadFile,
    ) -> Document:
        """
        Uploads a file, validates, saves to disk, creates a Document record,
        and dispatches a Celery task for processing.  Returns immediately.
        """
        # 1. Validate file extension
        raw_filename = file.filename or "unknown"
        safe_filename = _sanitize_filename(raw_filename)
        file_ext = safe_filename.rsplit(".", 1)[-1].lower() if "." in safe_filename else ""

        if file_ext not in SUPPORTED_FILE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: '.{file_ext}'. Supported: {', '.join(sorted(SUPPORTED_FILE_TYPES))}"
            )

        # 2. Validate client-provided MIME type (defense in depth)
        client_mime = file.content_type or ""
        expected_mimes = EXTENSION_MIME_MAP.get(file_ext, set())
        if client_mime and client_mime not in expected_mimes and client_mime not in ALLOWED_MIME_TYPES:
            logger.warning(
                f"Suspicious MIME type '{client_mime}' for .{file_ext} file. "
                f"Expected one of: {expected_mimes}"
            )

        # 3. Generate safe storage path using UUID (never use user-provided filename as path)
        doc_id = generate_uuid()
        storage_filename = f"doc_{doc_id}.{file_ext}"
        storage_dir = cls._get_storage_dir(org_id)
        file_path = os.path.join(storage_dir, storage_filename)

        # 4. Stream file to disk — never load entire file into memory
        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        file_size = 0

        try:
            with open(file_path, "wb") as f:
                while True:
                    chunk = file.file.read(STREAM_READ_CHUNK_SIZE)
                    if not chunk:
                        break
                    file_size += len(chunk)
                    if file_size > max_size:
                        break
                    f.write(chunk)
        except Exception as write_err:
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.error(f"Failed to save uploaded file: {write_err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded file."
            )

        # 5. Validate file size
        if file_size > max_size:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed ({settings.MAX_UPLOAD_SIZE_MB} MB)."
            )

        if file_size == 0:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty."
            )

        # 6. Detect actual MIME type from file content
        detected_mime = _detect_mime_type(file_path)

        # 7. Create Document record
        document = Document(
            id=doc_id,
            chatbot_id=chatbot_id,
            org_id=org_id,
            filename=safe_filename,
            storage_path=file_path,
            file_type=file_ext,
            mime_type=detected_mime or client_mime,
            file_size_bytes=file_size,
            status=DocumentStatusEnum.QUEUED,
            processing_stage="queued",
            progress=0,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        # 8. Dispatch document to native background worker queue
        try:
            from app.worker.background_worker import document_worker_queue
            task_id = document_worker_queue.submit_task(document.id)

            document.celery_task_id = task_id
            db.commit()

            logger.info(
                f"Document {document.id} queued for background processing "
                f"(task_id={task_id}, size={file_size} bytes)"
            )
        except Exception as e:
            logger.error(f"Failed to queue document for processing: {e}")
            document.status = DocumentStatusEnum.FAILED
            document.error_message = "Failed to queue document for processing."
            db.commit()

        return document

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
        """Deletes a document, its chunks, and removes the file from disk."""
        document = cls.get_document(db, org_id, document_id)

        # Delete file from disk (best effort)
        try:
            if document.storage_path and os.path.exists(document.storage_path):
                os.remove(document.storage_path)
        except OSError as e:
            logger.warning(f"Failed to delete file {document.storage_path}: {e}")

        # Delete from database (cascades to chunks via FK)
        db.delete(document)
        db.commit()


def mark_stale_documents_as_failed(db: Session) -> int:
    """
    Called on server startup.  Finds any documents stuck in active processing
    states (from a previous crash/restart) and marks them as FAILED.
    Returns the count of stale documents found.
    """
    stmt = select(Document).where(Document.status.in_(list(ACTIVE_STATUSES)))
    stale_docs = list(db.execute(stmt).scalars().all())

    for doc in stale_docs:
        doc.status = DocumentStatusEnum.FAILED
        doc.processing_stage = "failed"
        doc.error_message = "Processing was interrupted by a server restart. Please re-upload."

    if stale_docs:
        db.commit()
        logger.warning(f"Marked {len(stale_docs)} stale documents as FAILED on startup.")

    return len(stale_docs)
