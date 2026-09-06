from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Chatbot Builder"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = "super-secret-dev-jwt-key-change-in-production-1234567890"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = "postgresql://neondb_owner:npg_s7SWUgdQ2upP@ep-silent-poetry-ay7h6lo5-pooler.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

    # Redis (Celery broker + backend)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Gemini API & Embeddings
    GEMINI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "gemini-embedding-001"

    # Document Upload
    MAX_UPLOAD_SIZE_MB: int = 500
    UPLOAD_DIR: str = "./uploads"

    # Chunking Defaults
    DEFAULT_CHUNK_SIZE: int = 1000
    DEFAULT_CHUNK_OVERLAP: int = 200

    # Worker Configuration
    WORKER_CONCURRENCY: int = 2
    EMBEDDING_BATCH_SIZE: int = 20
    CHUNK_BATCH_SIZE: int = 50
    MAX_RETRIES: int = 3
    MAX_CHUNKS_PER_DOCUMENT: int = 5000

    # Chat Settings
    MAX_CONVERSATION_HISTORY: int = 20  # Max messages loaded for AI context
    MAX_CONTEXT_CHUNKS: int = 5  # Max vector search results per query
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
