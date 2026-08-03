from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.chatbot import Chatbot
from app.models.document import Document
from app.schemas.chatbot import ChatbotCreate, ChatbotUpdate
from app.services.vector_service import VectorService


class ChatbotService:
    @classmethod
    def create_chatbot(cls, db: Session, org_id: str, chatbot_in: ChatbotCreate) -> Chatbot:
        """Creates a new chatbot scoped to the given organization."""
        chatbot = Chatbot(
            org_id=org_id,
            name=chatbot_in.name,
            description=chatbot_in.description,
            system_prompt=chatbot_in.system_prompt,
            model_name=chatbot_in.model_name,
            temperature=chatbot_in.temperature,
        )
        db.add(chatbot)
        db.commit()
        db.refresh(chatbot)
        return chatbot

    @classmethod
    def list_chatbots(cls, db: Session, org_id: str) -> List[Chatbot]:
        """Lists all chatbots belonging to an organization."""
        stmt = select(Chatbot).where(Chatbot.org_id == org_id).order_by(Chatbot.created_at.desc())
        return list(db.execute(stmt).scalars().all())

    @classmethod
    def get_chatbot(cls, db: Session, org_id: str, chatbot_id: str) -> Chatbot:
        """Gets a single chatbot by ID, scoped to the given organization."""
        stmt = select(Chatbot).where(Chatbot.id == chatbot_id, Chatbot.org_id == org_id)
        chatbot = db.execute(stmt).scalars().first()
        if not chatbot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chatbot '{chatbot_id}' not found in this organization."
            )
        return chatbot

    @classmethod
    def update_chatbot(cls, db: Session, org_id: str, chatbot_id: str, update_in: ChatbotUpdate) -> Chatbot:
        """Partially updates a chatbot's configuration."""
        chatbot = cls.get_chatbot(db, org_id, chatbot_id)
        update_data = update_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(chatbot, field, value)

        db.commit()
        db.refresh(chatbot)
        return chatbot

    @classmethod
    def delete_chatbot(cls, db: Session, org_id: str, chatbot_id: str) -> None:
        """Deletes a chatbot and cascades to documents, chunks, and vectors."""
        chatbot = cls.get_chatbot(db, org_id, chatbot_id)

        # Delete vector collection for this chatbot
        VectorService.delete_collection(chatbot_id)

        db.delete(chatbot)
        db.commit()
