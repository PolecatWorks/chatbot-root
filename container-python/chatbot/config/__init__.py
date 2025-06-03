from .tool import ToolBoxConfig, ToolConfig
from pydantic import Field, BaseModel, validator
from chatbot.hams.config import HamsConfig
from pydantic import Field, BaseModel, SecretStr
from pydantic import HttpUrl
from pydantic_settings import BaseSettings, YamlConfigSettingsSource, SettingsConfigDict
from pydantic_file_secrets import FileSecretsSettingsSource
from pathlib import Path
from typing import Dict, Any, Self, List, Literal
from datetime import timedelta


import os


class BotConfig(BaseModel):
    """
    Configuration for the bot
    """

    api_path: str = Field(
        default="/api/messages",
        description="Path to the bot API",
    )
    app_id: str = Field(
        # default=DefaultConfig.APP_ID,
        description="Microsoft App ID",
    )
    app_password: SecretStr = Field(
        # default=DefaultConfig.APP_PASSWORD,
        description="Microsoft App Password",
    )


# TODO: Look here in future: https://github.com/pydantic/pydantic/discussions/2928#discussioncomment-4744841
class WebServerConfig(BaseModel):
    """
    Configuration for the web server
    """

    url: HttpUrl = Field(description="Host to listen on")
    prefix: str = Field(description="Prefix for the name of the resources")


# Define a timing object to capture time between event processing
class EventConfig(BaseModel):
    """
    Process costs for a given events
    """

    maxChunks: int = Field(
        description="Max number of chunks that can be processed after which cannot take more load"
    )
    chunkDuration: timedelta = Field(description="Duration of events")
    checkTime: timedelta = Field(description="Time between checking for new events")


class AIPromptConfig(BaseModel):
    text: str = Field(
        description="The text of the AI prompt",
    )


class MyAiConfig(BaseModel):
    """
    Configuration for the MyAI bot
    """

    system_instruction: List[AIPromptConfig] = Field(
        description="List of system instructions for the bot",
    )

    toolbox: ToolBoxConfig = Field(
        description="Default configuration for tool execution, including limits and enabled status",
    )


class LangchainConfig(BaseModel):
    """
    Configuration for LangChain, supporting both Azure OpenAI and GitHub-hosted models
    """
    model_provider: Literal["azure_openai", "github", "google_genai"] = Field(
        default="azure", description="Provider for the model: 'azure' or 'github'"
    )

    # Azure OpenAI settings
    azure_endpoint: HttpUrl | None = Field(
        default=None, description="Azure OpenAI endpoint for LangChain"
    )
    azure_api_key: SecretStr | None = Field(
        default=None, description="API key for Azure OpenAI access"
    )
    azure_deployment: str | None = Field(
        default=None, description="Azure OpenAI deployment name for LangChain"
    )
    azure_api_version: str | None = Field(
        default=None,
        description="API version for Azure OpenAI, default is None",
    )

    # GitHub-hosted model settings
    github_model_repo: str | None = Field(
        default=None,
        description="GitHub repository containing the model in owner/repo format",
    )
    github_api_base_url: HttpUrl | None = Field(
        default=None, description="Base URL for the GitHub model API endpoint"
    )
    github_api_key: SecretStr | None = Field(
        default=None,
        description="Optional API key for authenticated access to GitHub model",
    )
    google_api_key: SecretStr | None = Field(
        default=None,
        description="Optional API key for authenticated access to Genai model"
    )

    # Common settings
    model: str = Field(
        description="The model to use (e.g., 'gemini-1.5-flash-latest' or GitHub model name)"
    )
    temperature: float = Field(
        default=0.7,
        description="Temperature for the model, controlling randomness in responses",
    )
    context_length: int = Field(
        default=4096, description="Maximum context length for the model"
    )
    stop_sequences: List[str] = Field(
        default_factory=list, description="List of sequences that will stop generation"
    )
    timeout: int = Field(
        default=60, description="Timeout in seconds for model API calls"
    )
    streaming: bool = Field(
        default=True, description="Whether to stream responses from the model"
    )

    class Config:
        extra = "forbid"  # Prevents additional fields not defined in the model

    @validator("model_provider")
    def validate_provider_settings(cls, v, values):
        """Validate that the required settings are present for the chosen provider"""
        if v == "azure" and not (
            values.get("azure_openai_endpoint") and values.get("azure_deployment")
        ):
            raise ValueError(
                "Azure OpenAI settings required when model_provider is 'azure'"
            )
        elif v == "github" and not (
            values.get("github_model_repo") and values.get("github_api_base_url")
        ):
            raise ValueError(
                "GitHub model settings required when model_provider is 'github'"
            )
        return v


class ServiceConfig(BaseSettings):
    """
    Configuration for the service
    """

    logging: Dict[str, Any] = Field(description="Logging configuration")
    bot: BotConfig = Field(description="Bot configuration")
    aiclient: LangchainConfig = Field(description="AI Client configuration")
    myai: MyAiConfig = Field(description="MyAI bot configuration")

    webservice: WebServerConfig = Field(description="Web server configuration")
    hams: HamsConfig = Field(description="Health and monitoring configuration")
    events: EventConfig = Field(description="Process costs for events")

    model_config = SettingsConfigDict(
        # secrets_dir='/run/secrets',
        secrets_nested_subdir=True,
    )

    @classmethod
    def from_yaml(cls, config_path: Path, secrets_path: Path) -> Self:
        return cls(
            **YamlConfigSettingsSource(cls, config_path)(), _secrets_dir=secrets_path
        )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            FileSecretsSettingsSource(file_secret_settings),
        )
