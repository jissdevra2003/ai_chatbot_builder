import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine, SessionLocal
from app.models.base import Base
from app.routers import auth, invitations, chatbots, documents, chat

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure pgvector extension exists (Neon supports this natively)
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.info("pgvector extension verified.")
    except Exception as e:
        logger.warning(f"Could not create pgvector extension (may already exist or running SQLite): {e}")

    try:
        # Ensure database tables exist on startup
        Base.metadata.create_all(bind=engine)

        # Sync missing columns for documents and document_chunks tables if running on PostgreSQL
        if engine.dialect.name == "postgresql":
            with engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_path VARCHAR(1024) DEFAULT '' NOT NULL;
                    ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type VARCHAR(255);
                    ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_stage VARCHAR(50);
                    ALTER TABLE documents ADD COLUMN IF NOT EXISTS progress INTEGER DEFAULT 0 NOT NULL;
                    ALTER TABLE documents ADD COLUMN IF NOT EXISTS celery_task_id VARCHAR(255);

                    ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS org_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE;
                    ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS chatbot_id VARCHAR(36) REFERENCES chatbots(id) ON DELETE CASCADE;
                    ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS page_number INTEGER;
                    ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS metadata_json JSONB;
                    ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector(768);
                """))
                conn.commit()
                logger.info("Database schema columns synchronized.")
    except Exception as e:
        logger.warning(f"Could not sync database tables/columns on startup: {e}")

    # Mark any stale processing documents as FAILED
    try:
        from app.services.document_service import mark_stale_documents_as_failed
        db = SessionLocal()
        try:
            mark_stale_documents_as_failed(db)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not check for stale documents on startup: {e}")

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(invitations.router, prefix=settings.API_V1_STR)
app.include_router(chatbots.router, prefix=settings.API_V1_STR)
app.include_router(documents.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)




@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}
