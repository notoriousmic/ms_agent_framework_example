"""Configuration management with proper validation and environment handling."""

from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class AzureOpenAIConfig(BaseSettings):
    """Azure OpenAI specific configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str | None = Field(default=None, alias="AZURE_OPENAI_API_KEY", description="Azure OpenAI API key")
    endpoint: str | None = Field(
        default=None,
        alias="AZURE_OPENAI_ENDPOINT",
        description="Azure OpenAI endpoint URL",
    )
    api_version: str = Field(
        default="2024-02-01",
        alias="AZURE_OPENAI_API_VERSION",
        description="Azure OpenAI API version",
    )
    responses_deployment_name: str | None = Field(
        default=None,
        alias="AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME",
        description="Deployment name for responses",
    )

    @property
    def is_configured(self) -> bool:
        """Check if Azure OpenAI is properly configured."""
        return all([self.api_key, self.endpoint, self.responses_deployment_name])

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        """Ensure endpoint ends with /."""
        if v:
            return v.rstrip("/") + "/" if not v.endswith("/") else v
        return v


class ObservabilityConfig(BaseSettings):
    """Observability and tracing configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    enable_otel: bool = Field(default=True, alias="ENABLE_OTEL", description="Enable OpenTelemetry tracing")
    enable_sensitive_data: bool = Field(
        default=False,
        alias="ENABLE_SENSITIVE_DATA",
        description="Include sensitive data in traces",
    )
    otlp_endpoint: str | None = Field(default=None, alias="OTLP_ENDPOINT", description="OTLP endpoint for traces")
    applicationinsights_connection_string: str | None = Field(
        default=None,
        alias="APPLICATIONINSIGHTS_CONNECTION_STRING",
        description="Azure Application Insights connection string",
    )


class AzureAIFoundryConfig(BaseSettings):
    """Azure AI Foundry project configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_endpoint: str | None = Field(
        default=None,
        alias="PROJECT_ENDPOINT",
        description="Azure AI Foundry project endpoint",
    )
    model_deployment_name: str | None = Field(
        default="gpt-4o",
        description="Model deployment name for Azure AI Foundry agents",
    )
    subscription_id: str | None = Field(
        default=None, alias="AZURE_SUBSCRIPTION_ID", description="Azure subscription ID"
    )
    resource_group: str | None = Field(default=None, alias="AZURE_RESOURCE_GROUP", description="Azure resource group")
    project_name: str | None = Field(default=None, alias="AZURE_PROJECT_NAME", description="Azure project name")

    def model_post_init(self, __context) -> None:
        """Post-initialization to set environment variables for Azure AI library."""
        import os

        # Ensure Azure AI library can find the endpoint
        if self.project_endpoint and not os.getenv("AZURE_AI_PROJECT_ENDPOINT"):
            os.environ["AZURE_AI_PROJECT_ENDPOINT"] = self.project_endpoint
        # Set subscription ID for Azure AI library
        if self.subscription_id and not os.getenv("AZURE_SUBSCRIPTION_ID"):
            os.environ["AZURE_SUBSCRIPTION_ID"] = self.subscription_id

    @property
    def is_configured(self) -> bool:
        """Check if Azure AI Foundry is properly configured."""
        return self.project_endpoint is not None


class ToolsConfig(BaseSettings):
    """Tools and external services configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    brave_api_key: str | None = Field(default=None, alias="BRAVE_API_KEY", description="Brave Search API key")


class ResilienceConfig(BaseSettings):
    """Resilience and error handling configuration."""

    model_config = SettingsConfigDict(env_prefix="RESILIENCE_", env_file=".env", extra="ignore")

    # Global Retry Settings
    enable_retries: bool = Field(default=True, description="Enable retry logic globally")
    default_max_attempts: int = Field(default=3, description="Default maximum retry attempts")
    default_base_delay: float = Field(default=1.0, description="Default base delay between retries")
    default_max_delay: float = Field(default=60.0, description="Default maximum delay between retries")
    default_backoff_multiplier: float = Field(default=2.0, description="Default exponential backoff multiplier")
    default_enable_jitter: bool = Field(default=True, description="Enable jitter in retry delays by default")

    # Agent-specific Retry Settings
    agent_max_attempts: int = Field(default=3, description="Maximum retry attempts for agent operations")
    agent_base_delay: float = Field(default=2.0, description="Base delay for agent retries")
    agent_max_delay: float = Field(default=30.0, description="Maximum delay for agent retries")

    # API-specific Retry Settings
    api_max_attempts: int = Field(default=4, description="Maximum retry attempts for API operations")
    api_base_delay: float = Field(default=1.0, description="Base delay for API retries")
    api_max_delay: float = Field(default=60.0, description="Maximum delay for API retries")

    # Connection Settings
    connection_timeout: float = Field(default=30.0, description="Default connection timeout in seconds")
    read_timeout: float = Field(default=60.0, description="Default read timeout in seconds")
    connection_pool_size: int = Field(default=10, description="Default connection pool size")

    # Error Handling Settings
    enable_error_tracking: bool = Field(default=True, description="Enable detailed error tracking")
    max_error_context_length: int = Field(default=1000, description="Maximum length of error context")
    enable_error_notifications: bool = Field(default=False, description="Enable error notifications")

    # Timeout Settings
    agent_execution_timeout: float = Field(default=300.0, description="Agent execution timeout in seconds")
    tool_execution_timeout: float = Field(default=60.0, description="Tool execution timeout in seconds")
    api_request_timeout: float = Field(default=30.0, description="API request timeout in seconds")


class ApplicationConfig(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Application environment")
    debug: bool = Field(default=True, description="Enable debug mode")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=1, description="Number of API workers")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Path | None = Field(default=None, description="Log file path")

    # Agent Configuration
    default_max_tokens: int = Field(default=4000, description="Default max tokens for agents")
    default_temperature: float = Field(default=0.7, description="Default temperature for agents")
    agent_timeout: int = Field(default=300, description="Agent execution timeout in seconds")

    @field_validator("environment", mode="before")
    @classmethod
    def parse_environment(cls, v: str) -> Environment:
        """Parse environment from string."""
        if isinstance(v, str):
            return Environment(v.lower())
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == Environment.PRODUCTION


class Settings:
    """Centralized settings management."""

    def __init__(self):
        self._app: ApplicationConfig | None = None
        self._azure: AzureOpenAIConfig | None = None
        self._observability: ObservabilityConfig | None = None
        self._tools: ToolsConfig | None = None
        self._azure_ai_foundry: AzureAIFoundryConfig | None = None
        self._resilience: ResilienceConfig | None = None

    @property
    def app(self) -> ApplicationConfig:
        """Get application configuration."""
        if self._app is None:
            self._app = ApplicationConfig()
        return self._app

    @property
    def azure(self) -> AzureOpenAIConfig:
        """Get Azure OpenAI configuration."""
        if self._azure is None:
            self._azure = AzureOpenAIConfig()
        return self._azure

    @property
    def observability(self) -> ObservabilityConfig:
        """Get observability configuration."""
        if self._observability is None:
            self._observability = ObservabilityConfig()
        return self._observability

    @property
    def tools(self) -> ToolsConfig:
        """Get tools configuration."""
        if self._tools is None:
            self._tools = ToolsConfig()
        return self._tools

    @property
    def azure_ai_foundry(self) -> AzureAIFoundryConfig:
        """Get Azure AI Foundry configuration."""
        if self._azure_ai_foundry is None:
            self._azure_ai_foundry = AzureAIFoundryConfig()
        return self._azure_ai_foundry

    @property
    def resilience(self) -> ResilienceConfig:
        """Get resilience configuration."""
        if self._resilience is None:
            self._resilience = ResilienceConfig()
        return self._resilience

    def reload(self) -> None:
        """Reload all configurations."""
        self._app = None
        self._azure = None
        self._observability = None
        self._tools = None
        self._azure_ai_foundry = None
        self._resilience = None


# Global settings instance
settings = Settings()
