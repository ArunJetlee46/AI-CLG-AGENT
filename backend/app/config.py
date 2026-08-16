from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Beru Campus AI"
    app_env: str = "development"
    debug: bool = True

    secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    database_url: str = "sqlite:///./beru.db"
    redis_url: str = "redis://localhost:6379/0"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "beru-neo4j"

    qdrant_url: str = "http://localhost:6333"
    vector_store_backend: str = "chroma"
    vector_store_dir: str = "chroma_data"
    vector_collection: str = "beru_documents"

    embedding_backend: str = "ollama"
    ollama_embedding_model: str = "nomic-embed-text"

    llm_provider_order: str = "groq,gemini,ollama"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    llm_timeout_seconds: int = 120
    llm_circuit_breaker_failures: int = 3

    # Use the LLM gateway for intent routing / planning (fallback: keyword rules)
    llm_router_enabled: bool = True

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "bge-reranker-base"
    rag_top_k: int = 4
    rag_candidates: int = 20
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 150

    mlflow_tracking_uri: str = "http://localhost:5000"
    prediction_model_path: str = "models/risk_model.joblib"

    # Data directory - can be overridden via env var; defaults to ../data for local dev, /app/data for Docker
    data_dir: str = "../data"
    knowledge_data_dir: str = "../data"
    knowledge_source_label: str = "Anna University AI&DS Regulations 2021"

    curriculum_rag_enabled: bool = True
    curriculum_rag_jsonl: str = "../data/anna_university_aids_reg2021_rag.jsonl"
    curriculum_course_index_json: str = "../data/course_index.json"
    curriculum_collection: str = "curriculum_documents"
    curriculum_similarity_threshold: float = 0.35
    curriculum_regulation: str = "Regulations 2021"
    curriculum_programme: str = "B.Tech Artificial Intelligence and Data Science"
    curriculum_top_k: int = 6
    curriculum_candidates: int = 20

    default_admin_user: str = "admin"
    default_admin_password: str = "admin123"
    demo_student_id: str = "STU00000"
    demo_lecturer_id: str = "LEC0000"

    sentry_dsn: str = ""

    @property
    def llm_providers(self) -> list[str]:
        return [p.strip().lower() for p in self.llm_provider_order.split(",") if p.strip()]

    @property
    def data_path(self) -> Path:
        """Resolve data directory - works for both local dev and Docker."""
        return Path(self.data_dir).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
