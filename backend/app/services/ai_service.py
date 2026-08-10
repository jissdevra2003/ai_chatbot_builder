"""
AI Service — Gemini API wrapper for generating chat responses.
Handles prompt construction, API calls, and error handling.
"""
import logging
from typing import List, Tuple, Optional
from google import genai
from google.genai import types
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """Wrapper around Google Gemini API for chat response generation."""

    _client: Optional[genai.Client] = None

    @classmethod
    def _get_client(cls) -> genai.Client:
        """Returns a singleton Gemini client."""
        if cls._client is None:
            if not settings.GEMINI_API_KEY:
                raise ValueError(
                    "GEMINI_API_KEY is not configured. "
                    "Get your API key from https://aistudio.google.com/apikey "
                    "and set it in your .env file."
                )
            cls._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return cls._client

    @classmethod
    def _build_context_block(cls, context_chunks: List[str], source_filenames: List[str]) -> str:
        """Builds a formatted context block from retrieved document chunks."""
        if not context_chunks:
            return ""

        context_parts = []
        for i, (chunk, filename) in enumerate(zip(context_chunks, source_filenames), 1):
            context_parts.append(f"[Source {i}: {filename}]\n{chunk}")

        return (
            "--- RELEVANT KNOWLEDGE BASE DOCUMENTS ---\n"
            "Use the following information to answer the user's question. "
            "If the answer is not found in these documents, say so honestly.\n\n"
            + "\n\n".join(context_parts)
            + "\n--- END OF DOCUMENTS ---"
        )

    @classmethod
    def _build_conversation_history(
        cls, history: List[dict]
    ) -> List[types.Content]:
        """
        Converts stored message history into Gemini API content format.
        
        Args:
            history: List of dicts with 'role' and 'content' keys.
                     role is 'user' or 'bot'.
        """
        contents = []
        for msg in history:
            # Gemini uses 'user' and 'model' roles
            role = "user" if msg["role"] == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])]
                )
            )
        return contents

    @classmethod
    def generate_response(
        cls,
        system_prompt: str,
        context: str,
        conversation_history: List[dict],
        user_message: str,
        model_name: str = "gemini-2.0-flash",
        temperature: float = 0.7,
    ) -> Tuple[str, int]:
        """
        Generates a chat response using the Gemini API.

        Args:
            system_prompt: The chatbot's system instruction.
            context: Formatted context from retrieved document chunks.
            conversation_history: List of previous messages [{"role": "user"/"bot", "content": "..."}].
            user_message: The current user question/message.
            model_name: Gemini model to use.
            temperature: Response creativity (0.0 = deterministic, 2.0 = very creative).

        Returns:
            Tuple of (response_text, tokens_used).
        """
        client = cls._get_client()

        # Build the full system instruction with context
        full_system_instruction = system_prompt
        if context:
            full_system_instruction += f"\n\n{context}"

        # Build conversation contents for multi-turn
        contents = cls._build_conversation_history(conversation_history)

        # Add the current user message
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_message)]
            )
        )

        # Generate response
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=full_system_instruction,
                    temperature=temperature,
                    max_output_tokens=2048,
                )
            )

            response_text = response.text or "I'm sorry, I couldn't generate a response."

            # Extract token usage
            tokens_used = 0
            if response.usage_metadata:
                tokens_used = (
                    (response.usage_metadata.prompt_token_count or 0)
                    + (response.usage_metadata.candidates_token_count or 0)
                )

            return response_text, tokens_used

        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise ValueError(f"Failed to generate AI response: {str(e)}")

    @classmethod
    def get_embedding(cls, text: str) -> List[float]:
        """Generates a single vector embedding for text using Gemini Embedding API."""
        if not text or not text.strip():
            return []
        client = cls._get_client()
        try:
            res = client.models.embed_content(
                model=settings.EMBEDDING_MODEL,
                contents=text.strip()
            )
            if res.embeddings and len(res.embeddings) > 0:
                return res.embeddings[0].values
            return []
        except Exception as e:
            logger.error(f"Gemini embedding API error: {str(e)}")
            raise ValueError(f"Failed to generate embedding: {str(e)}")

    @classmethod
    def generate_embeddings(cls, texts: List[str], batch_size: int = 50) -> List[List[float]]:
        """
        Generates vector embeddings for a list of text strings in batches using Gemini API.
        
        Args:
            texts: List of text chunk strings.
            batch_size: Number of texts per API call (default: 50).
            
        Returns:
            List of embedding vectors (list of float lists).
        """
        if not texts:
            return []

        client = cls._get_client()
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                res = client.models.embed_content(
                    model=settings.EMBEDDING_MODEL,
                    contents=batch
                )
                if res.embeddings:
                    all_embeddings.extend([emb.values for emb in res.embeddings])
            except Exception as e:
                logger.error(f"Gemini batch embedding API error (batch index {i}): {str(e)}")
                raise ValueError(f"Failed to generate batch embeddings: {str(e)}")

        return all_embeddings

