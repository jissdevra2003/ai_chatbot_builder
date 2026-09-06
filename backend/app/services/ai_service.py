"""
AI Service — Gemini API wrapper for generating chat responses.
Handles prompt construction, API calls, and error handling.
"""
import logging
from datetime import datetime, timezone
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
        today_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

        if not context_chunks:
            return f"SYSTEM TEMPORAL CONTEXT: Today's date is {today_str}."

        context_parts = []
        for i, (chunk, filename) in enumerate(zip(context_chunks, source_filenames), 1):
            context_parts.append(f"[Source {i}: {filename}]\n{chunk}")

        return (
            f"SYSTEM TEMPORAL CONTEXT: Today's date is {today_str}.\n\n"
            "--- RELEVANT KNOWLEDGE BASE DOCUMENTS ---\n"
            "Use the following uploaded documents as the primary factual source to answer the user's question.\n\n"
            "CRITICAL DIRECTIVES:\n"
            "1. Treat all events, dates, numbers, and facts in the Knowledge Base documents below as ACCURATE REALITY.\n"
            "2. Do NOT claim recent events or dates mentioned in the documents (such as 2026) are in the future or haven't occurred yet.\n"
            "3. Structure your answer using clear Markdown formatting with bold headers and bullet points.\n"
            "4. Add double line breaks between sections for clean spacing.\n"
            "5. Keep the tone helpful, professional, and easy to read.\n"
            "6. If the answer is not found in these documents, say so honestly.\n\n"
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
        model_name: str = "gemini-3.6-flash",
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
                contents=text.strip(),
                config={"output_dimensionality": 768},
            )
            if res.embeddings and len(res.embeddings) > 0:
                return res.embeddings[0].values
            return []
        except Exception as e:
            logger.error(f"Gemini embedding API error: {str(e)}")
            raise ValueError(f"Failed to generate embedding: {str(e)}")

    @classmethod
    def generate_embeddings(cls, texts: List[str], batch_size: int = 20, max_retries: int = 3) -> List[List[float]]:
        """
        Generates vector embeddings for a list of text strings in batches using Gemini API.
        Includes retry logic with exponential backoff for transient API failures.
        
        Args:
            texts: List of text chunk strings.
            batch_size: Number of texts per API call (default: 50).
            max_retries: Max retry attempts per batch (default: 3).
            
        Returns:
            List of embedding vectors (list of float lists).
            
        Raises:
            ValueError: If embedding generation fails after all retries.
        """
        import time as _time

        if not texts:
            return []

        client = cls._get_client()
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            last_error = None

            for attempt in range(1, max_retries + 1):
                try:
                    res = client.models.embed_content(
                        model=settings.EMBEDDING_MODEL,
                        contents=batch,
                        config={"output_dimensionality": 768},
                    )
                    if res.embeddings:
                        all_embeddings.extend([emb.values for emb in res.embeddings if emb.values is not None])
                    last_error = None
                    break  # Success — move to next batch
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        wait = 2 ** attempt  # 2s, 4s, 8s
                        logger.warning(
                            f"Gemini embedding batch {i} attempt {attempt}/{max_retries} failed: {e}. "
                            f"Retrying in {wait}s..."
                        )
                        _time.sleep(wait)
                    else:
                        logger.error(f"Gemini embedding batch {i} failed after {max_retries} attempts: {e}")

            if last_error:
                raise ValueError(
                    f"Embedding generation failed after {max_retries} retries for batch starting at index {i}: "
                    f"{str(last_error)}"
                )

        return all_embeddings

