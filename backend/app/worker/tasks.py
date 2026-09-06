"""
Background worker task for document processing.

Pipeline:  EXTRACTING → CHUNKING → EMBEDDING → INDEXING → COMPLETED

Memory-efficient design:
  - Extracts text page-by-page (generator)
  - Chunks text block-by-block (generator)
  - Embeds in batches of EMBEDDING_BATCH_SIZE
  - Inserts chunks+embeddings in batches of CHUNK_BATCH_SIZE
  - Releases memory after each batch

Idempotency:
  - Deletes existing chunks for this document before inserting
  - Unique constraint (document_id, chunk_index) as safety net

Crash safety:
  - Handled in background threads without blocking main API server
  - Document marked FAILED on permanent errors
"""
import logging
import time
import traceback
from typing import List, Tuple

from sqlalchemy import select, delete

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.base import generate_uuid
from app.models.document import Document, DocumentChunk, DocumentStatusEnum

logger = logging.getLogger(__name__)


def _update_document_status(
    db,
    document_id: str,
    status: DocumentStatusEnum,
    processing_stage: str | None = None,
    progress: int | None = None,
    error_message: str | None = None,
    chunk_count: int | None = None,
) -> None:
    """Helper to update document processing status in the database."""
    doc = db.execute(select(Document).where(Document.id == document_id)).scalars().first()
    if not doc:
        return

    doc.status = status
    if processing_stage is not None:
        doc.processing_stage = processing_stage
    if progress is not None:
        doc.progress = progress
    if error_message is not None:
        doc.error_message = error_message
    if chunk_count is not None:
        doc.chunk_count = chunk_count

    db.commit()


def _generate_embeddings_batch(client, texts: List[str]) -> List[List[float]]:
    """
    Generates 768-dim embeddings for a batch of texts with retry logic.
    Returns a list of embedding vectors.
    """
    if not texts:
        return []

    max_retries = settings.MAX_RETRIES
    retry_delay = 2

    for attempt in range(1, max_retries + 1):
        try:
            res = client.models.embed_content(
                model=settings.EMBEDDING_MODEL,
                contents=texts,
                config={"output_dimensionality": 768},
            )
            if res.embeddings:
                return [emb.values for emb in res.embeddings]
            raise ValueError("Empty embeddings returned from API")
        except Exception as e:
            if attempt < max_retries:
                wait = retry_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"Embedding batch attempt {attempt}/{max_retries} failed: {e}. "
                    f"Retrying in {wait}s..."
                )
                time.sleep(wait)
            else:
                raise

    raise RuntimeError(f"Failed to generate embeddings after {max_retries} retries")



def process_document_task(document_id: str) -> dict:
    """
    Main document processing pipeline.

    Stages:
        1. EXTRACTING — Parse file to text (page-by-page)
        2. CHUNKING — Split text into overlapping chunks
        3. EMBEDDING — Generate embeddings in batches
        4. INDEXING — Bulk insert chunks + embeddings to PostgreSQL
        5. COMPLETED — Final status update

    Returns:
        Dict with processing result summary.
    """
    start_time = time.time()
    db = SessionLocal()

    try:
        # Fetch document record
        document = db.execute(
            select(Document).where(Document.id == document_id)
        ).scalars().first()

        if not document:
            logger.error(f"Document {document_id} not found in database")
            return {"status": "error", "message": "Document not found"}

        logger.info(
            f"Processing document {document_id}: "
            f"filename={document.filename}, "
            f"size={document.file_size_bytes} bytes, "
            f"org_id={document.org_id}"
        )

        # ── Stage 1: EXTRACTING ──────────────────────────────────────
        _update_document_status(
            db, document_id,
            status=DocumentStatusEnum.EXTRACTING,
            processing_stage="extracting",
            progress=5,
        )

        from app.worker.extraction import extract_file

        file_path = document.storage_path
        file_type = document.file_type

        logger.info(f"[{document_id}] Extracting {file_type}: {file_path}")

        # Collect text blocks from extraction (generator)
        text_blocks: List[Tuple[int, str]] = []
        total_chars = 0

        for page_num, text in extract_file(file_path, file_type):
            text_blocks.append((page_num, text))
            total_chars += len(text)

        if total_chars == 0:
            raise ValueError("No text content could be extracted from the file.")

        logger.info(f"[{document_id}] Extracted {total_chars} chars from {len(text_blocks)} text blocks")

        _update_document_status(
            db, document_id,
            status=DocumentStatusEnum.CHUNKING,
            processing_stage="chunking",
            progress=20,
        )

        # ── Stage 2: CHUNKING ────────────────────────────────────────
        from app.worker.chunking import chunk_extracted_text

        chatbot_id = document.chatbot_id
        org_id = document.org_id

        # Get chatbot chunking config
        from app.models.chatbot import Chatbot
        chatbot = db.execute(select(Chatbot).where(Chatbot.id == chatbot_id)).scalars().first()
        chunk_size = chatbot.chunk_size if chatbot else settings.DEFAULT_CHUNK_SIZE
        chunk_overlap = chatbot.chunk_overlap if chatbot else settings.DEFAULT_CHUNK_OVERLAP

        # Generate chunks (generator from text blocks)
        all_chunks: List[Tuple[int, str, int]] = []
        for chunk_index, content, page_number in chunk_extracted_text(
            iter(text_blocks),
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            max_chunks=settings.MAX_CHUNKS_PER_DOCUMENT,
        ):
            all_chunks.append((chunk_index, content, page_number))

        # Free text blocks memory
        del text_blocks

        if not all_chunks:
            raise ValueError("Text chunking produced zero chunks.")

        total_chunks = len(all_chunks)
        logger.info(f"[{document_id}] Chunked into {total_chunks} pieces")

        _update_document_status(
            db, document_id,
            status=DocumentStatusEnum.EMBEDDING,
            processing_stage="embedding",
            progress=30,
        )

        # ── Stage 3: EMBEDDING (batched) ─────────────────────────────
        from google import genai

        gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        batch_size = settings.EMBEDDING_BATCH_SIZE

        # Process embeddings in batches and pair with chunk data
        chunk_records: List[dict] = []
        total_batches = (total_chunks + batch_size - 1) // batch_size

        for batch_idx in range(0, total_chunks, batch_size):
            batch_end = min(batch_idx + batch_size, total_chunks)
            batch_chunks = all_chunks[batch_idx:batch_end]
            batch_texts = [content for _, content, _ in batch_chunks]

            # Generate embeddings for this batch
            embeddings = _generate_embeddings_batch(gemini_client, batch_texts)

            # Pair chunks with embeddings
            for i, (chunk_index, content, page_number) in enumerate(batch_chunks):
                chunk_records.append({
                    "chunk_index": chunk_index,
                    "content": content,
                    "page_number": page_number,
                    "embedding": embeddings[i],
                    "char_count": len(content),
                })

            # Update progress (30% to 80% range for embedding stage)
            current_batch = (batch_idx // batch_size) + 1
            embed_progress = 30 + int((current_batch / total_batches) * 50)
            _update_document_status(
                db, document_id,
                processing_stage="embedding",
                status=DocumentStatusEnum.EMBEDDING,
                progress=min(embed_progress, 80),
            )

            logger.info(
                f"[{document_id}] Embedded batch {current_batch}/{total_batches} "
                f"({batch_end}/{total_chunks} chunks)"
            )

            # Small delay between batches to avoid API rate limits
            if batch_end < total_chunks:
                time.sleep(0.2)

        # Free the raw chunks list
        del all_chunks

        # ── Stage 4: INDEXING (bulk insert) ──────────────────────────
        _update_document_status(
            db, document_id,
            status=DocumentStatusEnum.INDEXING,
            processing_stage="indexing",
            progress=85,
        )

        logger.info(f"[{document_id}] Indexing {total_chunks} chunks into database")

        # Delete any existing chunks for this document (idempotent retry)
        db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        db.flush()

        # Bulk insert in batches
        insert_batch_size = settings.CHUNK_BATCH_SIZE
        for insert_idx in range(0, len(chunk_records), insert_batch_size):
            batch = chunk_records[insert_idx:insert_idx + insert_batch_size]

            for record in batch:
                db_chunk = DocumentChunk(
                    id=generate_uuid(),
                    document_id=document_id,
                    org_id=org_id,
                    chatbot_id=chatbot_id,
                    chunk_index=record["chunk_index"],
                    content=record["content"],
                    char_count=record["char_count"],
                    page_number=record["page_number"],
                    embedding=record["embedding"],
                    metadata_json={
                        "filename": document.filename,
                        "document_id": document_id,
                        "page_number": record["page_number"],
                    },
                )
                db.add(db_chunk)

            db.flush()

            # Update progress (85% to 95% range for indexing)
            idx_progress = 85 + int(
                ((insert_idx + len(batch)) / len(chunk_records)) * 10
            )
            _update_document_status(
                db, document_id,
                status=DocumentStatusEnum.INDEXING,
                processing_stage="indexing",
                progress=min(idx_progress, 95),
            )

        # Free chunk records memory
        del chunk_records

        # ── Stage 5: COMPLETED ───────────────────────────────────────
        elapsed = round(time.time() - start_time, 2)

        _update_document_status(
            db, document_id,
            status=DocumentStatusEnum.COMPLETED,
            processing_stage="completed",
            progress=100,
            chunk_count=total_chunks,
            error_message=None,
        )

        db.commit()

        logger.info(
            f"[{document_id}] ✅ Processing completed: "
            f"{total_chunks} chunks, {elapsed}s elapsed"
        )

        return {
            "status": "completed",
            "document_id": document_id,
            "chunk_count": total_chunks,
            "processing_time_seconds": elapsed,
        }

    except Exception as e:
        logger.error(f"[{document_id}] ❌ Processing failed: {e}")
        logger.error(traceback.format_exc())

        # Mark document as FAILED
        try:
            db.rollback()
            safe_error = str(e)[:2000]
            _update_document_status(
                db, document_id,
                status=DocumentStatusEnum.FAILED,
                processing_stage="failed",
                error_message=safe_error,
            )
        except Exception as db_err:
            logger.error(f"[{document_id}] Failed to update status to FAILED: {db_err}")

        return {
            "status": "failed",
            "document_id": document_id,
            "error": str(e)[:500],
        }

    finally:
        db.close()
