"""
Vector store service using ChromaDB for embedding storage and retrieval.
Scoped per-chatbot with org-level metadata filtering.
"""
from typing import List, Optional
import chromadb
from app.core.config import settings


# Singleton ChromaDB client
_chroma_client: Optional[chromadb.ClientAPI] = None


def get_chroma_client() -> chromadb.ClientAPI:
    """Returns a singleton ChromaDB persistent client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return _chroma_client


class VectorService:
    @classmethod
    def _collection_name(cls, chatbot_id: str) -> str:
        """Generates a ChromaDB collection name scoped to a chatbot."""
        return f"chatbot_{chatbot_id.replace('-', '_')}"

    @classmethod
    def get_or_create_collection(cls, chatbot_id: str) -> chromadb.Collection:
        """Gets or creates a ChromaDB collection for a specific chatbot."""
        client = get_chroma_client()
        return client.get_or_create_collection(
            name=cls._collection_name(chatbot_id),
            metadata={"chatbot_id": chatbot_id}
        )

    @classmethod
    def add_chunks(
        cls,
        chatbot_id: str,
        chunk_ids: List[str],
        chunk_texts: List[str],
        metadatas: List[dict],
        embeddings: Optional[List[List[float]]] = None
    ) -> None:
        """
        Adds text chunks with their embeddings to the chatbot's vector collection.
        
        Args:
            chatbot_id: The chatbot this data belongs to.
            chunk_ids: Unique IDs for each chunk (use DocumentChunk.id).
            chunk_texts: The raw text content of each chunk.
            metadatas: Metadata dicts for each chunk (document_id, org_id, etc.).
            embeddings: Pre-computed embedding vectors. If None, ChromaDB will
                       use its default embedding function.
        """
        collection = cls.get_or_create_collection(chatbot_id)
        add_kwargs = {
            "ids": chunk_ids,
            "documents": chunk_texts,
            "metadatas": metadatas,
        }
        if embeddings:
            add_kwargs["embeddings"] = embeddings
        collection.add(**add_kwargs)

    @classmethod
    def delete_document_vectors(cls, chatbot_id: str, document_id: str) -> None:
        """Deletes all vectors belonging to a specific document from the chatbot's collection."""
        try:
            collection = cls.get_or_create_collection(chatbot_id)
            collection.delete(where={"document_id": document_id})
        except Exception:
            # Collection may not exist yet if no documents were ever processed
            pass

    @classmethod
    def delete_collection(cls, chatbot_id: str) -> None:
        """Deletes the entire vector collection for a chatbot."""
        try:
            client = get_chroma_client()
            client.delete_collection(name=cls._collection_name(chatbot_id))
        except Exception:
            # Collection may not exist
            pass

    @classmethod
    def query(
        cls,
        chatbot_id: str,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 5,
        where_filter: Optional[dict] = None
    ) -> dict:
        """
        Queries the chatbot's vector collection for similar chunks.
        
        Args:
            chatbot_id: The chatbot to query against.
            query_texts: Optional list of query strings.
            query_embeddings: Optional pre-computed query embedding vectors.
            n_results: Number of results to return per query.
            where_filter: Optional metadata filter.
        
        Returns:
            ChromaDB query results dict with ids, documents, distances, metadatas.
        """
        collection = cls.get_or_create_collection(chatbot_id)
        query_kwargs = {
            "n_results": n_results,
        }
        if query_embeddings:
            query_kwargs["query_embeddings"] = query_embeddings
        elif query_texts:
            query_kwargs["query_texts"] = query_texts
        else:
            raise ValueError("Either query_texts or query_embeddings must be provided.")

        if where_filter:
            query_kwargs["where"] = where_filter
        return collection.query(**query_kwargs)

