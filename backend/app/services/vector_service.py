"""
Vector search service using pgvector for similarity queries.

All embeddings are stored directly in PostgreSQL via the pgvector extension.
Queries are scoped by chatbot_id and org_id for multi-tenant isolation.
"""
import logging
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.document import DocumentChunk

logger = logging.getLogger(__name__)


class VectorService:
    @classmethod
    def search_similar(
        cls,
        db: Session,
        chatbot_id: str,
        org_id: str,
        query_embedding: List[float],
        n_results: int = 5,
    ) -> List[dict]:
        """
        Searches for document chunks similar to the query embedding
        using pgvector cosine distance.

        Scoped by chatbot_id and org_id for tenant isolation.

        Args:
            db: Database session.
            chatbot_id: Chatbot to search within.
            org_id: Organization to scope the search to.
            query_embedding: Query vector (list of floats).
            n_results: Maximum number of results to return.

        Returns:
            List of dicts with keys: content, filename, chunk_index,
            page_number, document_id, distance.
        """
        if not query_embedding:
            return []

        try:
            # Convert embedding to pgvector format string
            embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

            # pgvector cosine distance query
            # <=> is the cosine distance operator (lower = more similar)
            query = text("""
                SELECT
                    dc.id,
                    dc.content,
                    dc.chunk_index,
                    dc.page_number,
                    dc.document_id,
                    dc.metadata_json,
                    dc.embedding <=> :embedding AS distance
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE dc.chatbot_id = :chatbot_id
                  AND dc.org_id = :org_id
                  AND dc.embedding IS NOT NULL
                  AND d.status = 'completed'
                ORDER BY dc.embedding <=> :embedding
                LIMIT :n_results
            """)

            results = db.execute(
                query,
                {
                    "embedding": embedding_str,
                    "chatbot_id": chatbot_id,
                    "org_id": org_id,
                    "n_results": n_results,
                },
            ).fetchall()

            search_results = []
            for row in results:
                metadata = row.metadata_json or {}
                search_results.append({
                    "content": row.content,
                    "filename": metadata.get("filename", "unknown"),
                    "chunk_index": row.chunk_index,
                    "page_number": row.page_number,
                    "document_id": row.document_id,
                    "distance": float(row.distance),
                })

            return search_results

        except Exception as e:
            logger.error(f"Vector search failed for chatbot {chatbot_id}: {e}")
            return []
