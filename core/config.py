"""
SHERLOCK Intelligence System - Configuration Management
Centralized configuration using pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    UPLOADS_DIR: Path = DATA_DIR / "uploads"
    PROCESSED_DIR: Path = DATA_DIR / "processed"
    QUARANTINE_DIR: Path = DATA_DIR / "quarantine"
    EMBEDDINGS_DIR: Path = DATA_DIR / "embeddings"
    GRAPHS_DIR: Path = DATA_DIR / "graphs"
    REPORTS_DIR: Path = DATA_DIR / "reports"
    KNOWLEDGE_BASE_DIR: Path = DATA_DIR / "knowledge_base"
    INVESTIGATIONS_DIR: Path = DATA_DIR / "investigations"
    LEDGER_DB_PATH: Path = DATA_DIR / "processing_ledger.db"
    REDIS_URL: Optional[str] = None  # e.g. redis://localhost:6379 for incremental queues

    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1

    EMBEDDING_PROVIDER: str = "local"  # "local" | "openai"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "sherlock123"
    NEO4J_DATABASE: str = "neo4j"

    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "sherlock_documents"

    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    SPACY_MODEL_PT: str = "pt_core_news_lg"
    SPACY_MODEL_EN: str = "en_core_web_lg"

    MAX_FILE_SIZE_MB: int = 100
    SUPPORTED_FORMATS: List[str] = [
        ".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls",
        ".csv", ".json", ".xml", ".html", ".eml", ".msg",
        ".png", ".jpg", ".jpeg", ".mp3", ".wav",
    ]

    TESSERACT_CMD: Optional[str] = None
    OCR_LANGUAGES: str = "por+eng"

    MIN_ENTITY_CONFIDENCE: float = 0.7
    ENTITY_TYPES: List[str] = [
        "PERSON", "ORG", "GPE", "LOC", "DATE",
        "MONEY", "PERCENT", "PHONE", "EMAIL",
    ]

    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.75
    MIN_SHARED_ENTITIES: int = 2
    MAX_LINKS_PER_DOCUMENT: int = 50

    OUTLIER_THRESHOLD: float = 3.0
    MIN_CLUSTER_SIZE: int = 3

    PQMS_GUARDIAN_THRESHOLD: float = 0.05
    PQMS_FIDELITY_MIN: float = 0.99
    PQMS_RCF_TARGET: float = 0.95

    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_PROJECT: str = "sherlock-intelligence"

    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path = PROJECT_ROOT / "sherlock.log"

    # Checkpointing (LangGraph - persist state between nodes for long runs)
    CHECKPOINT_DIR: Optional[Path] = None  # Set to PROJECT_ROOT / "checkpoints" to enable
    # Human-in-the-loop: pause before ODOS Guardian (Fase 4). Set False to run without interrupt.
    INTERRUPT_BEFORE_ODOS: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for dir_path in [
            self.DATA_DIR, self.UPLOADS_DIR, self.PROCESSED_DIR,
            self.QUARANTINE_DIR, self.EMBEDDINGS_DIR, self.GRAPHS_DIR,
            self.REPORTS_DIR, self.KNOWLEDGE_BASE_DIR, self.INVESTIGATIONS_DIR,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)


settings = Settings()
