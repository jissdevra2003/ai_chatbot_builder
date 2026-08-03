from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Chatbot Builder"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = "super-secret-dev-jwt-key-change-in-production-1234567890"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Defaults to SQLite local db if POSTGRES_URL not provided
    DATABASE_URL: str = "sqlite:///./chatbot_builder.db"

    # Phase 2: Gemini & Embeddings
    GEMINI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-004"

    # Phase 2: ChromaDB Vector Store
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # Phase 2: Document Upload
    MAX_UPLOAD_SIZE_MB: int = 20
    UPLOAD_DIR: str = "./uploads"

    # Phase 2: Chunking Defaults
    DEFAULT_CHUNK_SIZE: int = 1000
    DEFAULT_CHUNK_OVERLAP: int = 200
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
