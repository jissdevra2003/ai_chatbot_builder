"""
Chat Service — RAG pipeline orchestrator.
Connects VectorService (search) + AIService (Gemini) + Database (history).
This is the BRAIN of the chatbot.
"""
import json
import time
import uuid
import logging
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.core.config import settings
from app.models.chatbot import Chatbot
from app.models.conversation import Conversation
from app.models.message import Message, MessageRoleEnum
from app.schemas.chat import ChatResponse, ChatSourceDocument
from app.services.vector_service import VectorService
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


class ChatService:
    """Orchestrates the full chat pipeline: receive → search → generate → store → respond."""

    @classmethod
    def send_message(
        cls,
        db: Session,
        chatbot: Chatbot,
        message: str,
        session_id: Optional[str] = None,
    ) -> ChatResponse:
        """
        Processes a user message through the full RAG pipeline.

        Flow:
        1. Get or create Conversation (by session_id)
        2. Save user message to DB
        3. Load conversation history
        4. Search vector store for relevant chunks
        5. Build context from chunks
        6. Call Gemini API via AIService
        7. Save bot response to DB
        8. Return ChatResponse

        Args:
            db: Database session.
            chatbot: The Chatbot instance to chat with.
            message: User's message text.
            session_id: Optional session ID to continue existing conversation.

        Returns:
            ChatResponse with bot reply, sources, and metadata.
        """
        start_time = time.time()

        # --- Step 1: Get or create conversation ---
        conversation = cls._get_or_create_conversation(db, chatbot.id, session_id)

        # --- Step 2: Save user message ---
        user_msg = Message(
            conversation_id=conversation.id,
            role=MessageRoleEnum.USER,
            content=message,
        )
        db.add(user_msg)
        conversation.message_count += 1

        # Auto-title from first user message
        if conversation.title is None:
            conversation.title = message[:100] + ("..." if len(message) > 100 else "")

        db.flush()

        # --- Step 3: Load conversation history ---
        history = cls._load_history(db, conversation.id)

        # --- Step 4: Search vector store for relevant chunks ---
        context_chunks, source_docs = cls._search_knowledge_base(db, chatbot, message)

        # --- Step 5: Build context string ---
        context = AIService._build_context_block(
            context_chunks,
            [doc.filename for doc in source_docs]
        )

        # --- Step 6: Call Gemini API ---
        try:
            response_text, tokens_used = AIService.generate_response(
                system_prompt=chatbot.system_prompt,
                context=context,
                conversation_history=history,
                user_message=message,
                model_name=chatbot.model_name,
                temperature=chatbot.temperature,
            )
        except ValueError as e:
            # Save error as bot message so conversation state is consistent
            error_msg = f"I'm sorry, I encountered an error: {str(e)}"
            bot_msg = Message(
                conversation_id=conversation.id,
                role=MessageRoleEnum.BOT,
                content=error_msg,
            )
            db.add(bot_msg)
            conversation.message_count += 1
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e)
            )

        # --- Step 7: Save bot response ---
        elapsed_ms = int((time.time() - start_time) * 1000)

        sources_json = json.dumps([
            {"filename": doc.filename, "chunk_index": doc.chunk_index, "relevance_score": doc.relevance_score}
            for doc in source_docs
        ]) if source_docs else None

        bot_msg = Message(
            conversation_id=conversation.id,
            role=MessageRoleEnum.BOT,
            content=response_text,
            sources=sources_json,
            tokens_used=tokens_used,
            response_time_ms=elapsed_ms,
        )
        db.add(bot_msg)
        conversation.message_count += 1
        db.commit()

        # --- Step 8: Return response ---
        return ChatResponse(
            message=response_text,
            session_id=conversation.session_id,
            conversation_id=conversation.id,
            sources=source_docs,
            tokens_used=tokens_used,
            response_time_ms=elapsed_ms,
        )

    @classmethod
    def _get_or_create_conversation(
        cls,
        db: Session,
        chatbot_id: str,
        session_id: Optional[str] = None,
    ) -> Conversation:
        """Gets an existing conversation by session_id or creates a new one."""
        if session_id:
            stmt = select(Conversation).where(
                Conversation.session_id == session_id,
                Conversation.chatbot_id == chatbot_id,
            )
            conversation = db.execute(stmt).scalars().first()
            if conversation:
                if not conversation.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="This conversation has been closed."
                    )
                return conversation

        # Create new conversation
        new_session_id = session_id or str(uuid.uuid4())
        conversation = Conversation(
            chatbot_id=chatbot_id,
            session_id=new_session_id,
        )
        db.add(conversation)
        db.flush()
        return conversation

    @classmethod
    def _load_history(cls, db: Session, conversation_id: str) -> List[dict]:
        """Loads the last N messages from a conversation for context."""
        max_history = settings.MAX_CONVERSATION_HISTORY

        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(max_history)
        )
        messages = list(db.execute(stmt).scalars().all())
        messages.reverse()  # Oldest first

        # Exclude the message we just added (latest user message)
        # since it'll be sent separately to the AI
        if messages and messages[-1].role == MessageRoleEnum.USER:
            messages = messages[:-1]

        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]

    @classmethod
    def _search_knowledge_base(
        cls,
        db: Session,
        chatbot: Chatbot,
        query: str,
    ) -> tuple[List[str], List[ChatSourceDocument]]:
        """
        Searches the chatbot's vector store for chunks relevant to the query.
        Uses pgvector cosine similarity search.

        Returns:
            Tuple of (chunk_texts, source_documents).
        """
        n_results = settings.MAX_CONTEXT_CHUNKS

        try:
            query_vector = AIService.get_embedding(query)
            if not query_vector:
                logger.warning(f"Empty embedding for query, skipping vector search")
                return [], []

            results = VectorService.search_similar(
                db=db,
                chatbot_id=chatbot.id,
                org_id=chatbot.org_id,
                query_embedding=query_vector,
                n_results=n_results,
            )
        except Exception as e:
            logger.warning(f"Vector search failed for chatbot {chatbot.id}: {e}")
            return [], []

        if not results:
            return [], []

        chunk_texts = []
        source_docs = []

        for result in results:
            chunk_texts.append(result["content"])
            # pgvector cosine distance: lower = more similar. Convert to 0-1 relevance score
            relevance = max(0.0, 1.0 - (result["distance"] / 2.0))
            source_docs.append(ChatSourceDocument(
                filename=result.get("filename", "unknown"),
                chunk_index=result.get("chunk_index", 0),
                relevance_score=round(relevance, 3),
            ))

        return chunk_texts, source_docs

    # --- Conversation Management ---

    @classmethod
    def list_conversations(cls, db: Session, chatbot_id: str) -> List[Conversation]:
        """Lists all conversations for a chatbot, newest first."""
        stmt = (
            select(Conversation)
            .where(Conversation.chatbot_id == chatbot_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(db.execute(stmt).scalars().all())

    @classmethod
    def get_conversation(cls, db: Session, conversation_id: str) -> Conversation:
        """Gets a conversation with all its messages."""
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        conversation = db.execute(stmt).scalars().first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found."
            )
        return conversation

    @classmethod
    def get_conversation_messages(cls, db: Session, conversation_id: str) -> List[Message]:
        """Gets all messages for a conversation, ordered by time."""
        # Verify conversation exists
        cls.get_conversation(db, conversation_id)

        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        return list(db.execute(stmt).scalars().all())

    @classmethod
    def delete_conversation(cls, db: Session, conversation_id: str) -> None:
        """Deletes a conversation and all its messages."""
        conversation = cls.get_conversation(db, conversation_id)
        db.delete(conversation)
        db.commit()
