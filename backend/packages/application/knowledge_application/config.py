from __future__ import annotations

from dataclasses import dataclass
import os


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = "development"
    database_url: str = "sqlite:///./storage/knowledge.db"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    provider_mode: str = "mock"
    ai_mode: str = "mock"
    parser_mode: str = "mock"
    mcp_mode: str = "mock"
    storage_dir: str = "storage/objects"
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_api_key: str = ""
    chat_model: str = "deepseek-ai/DeepSeek-V3"
    embedding_model: str = "BAAI/bge-large-zh-v1.5"
    rerank_model: str = "Pro/BAAI/bge-reranker-v2-m3"
    mcp_url: str = ""
    mcp_api_key: str = ""
    mcp_tool_name: str = ""
    mineru_base_url: str = "https://mineru.net/api/v4"
    mineru_api_key: str = ""
    milvus_uri: str = "http://milvus:19530"
    milvus_token: str = ""
    milvus_collection: str = "knowledge_chunks_v1"
    index_version: str = "bge-large-zh-v1.5-v1"
    embedding_dimension: int = 1024
    auto_create_schema: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        environment = os.getenv("APP_ENV", "development")
        secret = os.getenv("JWT_SECRET", "development-only-change-me")
        if environment in {"production", "staging"} and secret == "development-only-change-me":
            raise RuntimeError("JWT_SECRET must be configured outside development")
        settings = cls(
            environment=environment,
            database_url=os.getenv("DATABASE_URL", "sqlite:///./storage/knowledge.db"),
            redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
            jwt_secret=secret,
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            access_token_minutes=int(os.getenv("ACCESS_TOKEN_MINUTES", "30")),
            provider_mode=os.getenv("PROVIDER_MODE", "mock"),
            ai_mode=os.getenv("AI_MODE", os.getenv("PROVIDER_MODE", "mock")),
            parser_mode=os.getenv("PARSER_MODE", "mock"),
            mcp_mode=os.getenv("MCP_MODE", "mock"),
            storage_dir=os.getenv("STORAGE_DIR", "storage/objects"),
            siliconflow_base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
            siliconflow_api_key=os.getenv("SILICONFLOW_API_KEY", ""),
            chat_model=os.getenv("CHAT_MODEL", "deepseek-ai/DeepSeek-V3"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5"),
            rerank_model=os.getenv("RERANK_MODEL", "Pro/BAAI/bge-reranker-v2-m3"),
            mcp_url=os.getenv("MCP_URL", os.getenv("MODELSCOPE_BASE_URL", "")),
            mcp_api_key=os.getenv("MCP_API_KEY", os.getenv("MODELSCOPE_API_KEY", "")),
            mcp_tool_name=os.getenv("MCP_TOOL_NAME", ""),
            mineru_base_url=os.getenv("MINERU_BASE_URL", "https://mineru.net/api/v4"),
            mineru_api_key=os.getenv("MINERU_API_KEY", ""),
            milvus_uri=os.getenv("MILVUS_URI", "http://milvus:19530"),
            milvus_token=os.getenv("MILVUS_TOKEN", ""),
            milvus_collection=os.getenv("MILVUS_COLLECTION", "knowledge_chunks_v1"),
            index_version=os.getenv("INDEX_VERSION", "bge-large-zh-v1.5-v1"),
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1024")),
            # Local development needs a usable empty database on first start;
            # production and staging still require explicit migrations.
            auto_create_schema=_bool_env("AUTO_CREATE_SCHEMA", environment in {"development", "test"}),
        )
        if settings.ai_mode == "live" and not settings.siliconflow_api_key:
            raise RuntimeError("SILICONFLOW_API_KEY is required when AI_MODE=live")
        if settings.mcp_mode == "live" and (not settings.mcp_url or not settings.mcp_api_key):
            raise RuntimeError("MCP_URL and MCP_API_KEY are required when MCP_MODE=live")
        if settings.parser_mode == "live" and not settings.mineru_api_key:
            raise RuntimeError("MINERU_API_KEY is required when PARSER_MODE=live")
        return settings
