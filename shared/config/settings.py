"""Application settings loaded from environment variables.

Uses pydantic-settings for validated, typed configuration.
"""

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Root application settings — shared across all services."""

    # General
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"

    # Service ports
    gateway_port: int = 8000
    computation_port: int = 8001
    reports_port: int = 8002
    frontend_port: int = 3000

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM (LiteLLM)
    litellm_model: str = "azure/gpt-4o"
    litellm_fast_model: str = "azure/gpt-4o-mini"
    litellm_embedding_model: str = "azure/text-embedding-3-small"
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_version: str = "2024-02-01"

    # LLM Configuration (SD-14)
    anthropic_api_key: Optional[str] = None
    use_llm_agents: bool = True
    llm_provider: str = "anthropic"  # "anthropic" or "azure"

    # Azure AD
    azure_ad_tenant_id: Optional[str] = None
    azure_ad_client_id: Optional[str] = None
    azure_ad_client_secret: Optional[str] = None

    # Databricks (Phase 2)
    databricks_host: Optional[str] = None
    databricks_token: Optional[str] = None
    databricks_sql_warehouse_id: Optional[str] = None
    databricks_catalog: str = "variance_agent"
    databricks_schema: str = "gold"

    # Vector Store
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None

    # Notifications
    teams_webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    notification_from_email: str = "variance-agent@company.com"

    # Database (PostgreSQL)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/variance_agent"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/variance_agent"

    # Service-to-service
    computation_service_url: str = "http://localhost:8001"

    # Data
    synthetic_data_path: str = "data/output"
    synthetic_data_seed: int = 42

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        # Also search project root for .env (handles different cwd)
        "env_file": [".env", "../.env", "../../.env"],
    }
