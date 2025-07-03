from .tool import ToolBoxConfig, ToolConfig
from pydantic import Field, BaseModel
from customer.hams.config import HamsConfig
from pydantic import Field, BaseModel, SecretStr, field_validator
from pydantic import HttpUrl
from pydantic_settings import BaseSettings, YamlConfigSettingsSource, SettingsConfigDict
from pydantic_file_secrets import FileSecretsSettingsSource
from pathlib import Path
from typing import Any, Self, Literal # TODO: Review Self and Literal for Python version compatibility
from datetime import timedelta


import os


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

    system_instruction: list[AIPromptConfig] = Field(
        description="List of system instructions for the bot",
    )

    toolbox: ToolBoxConfig = Field(
        description="Default configuration for tool execution, including limits and enabled status",
    )


class ServiceConfig(BaseSettings):
    """
    Configuration for the service
    """

    logging: dict[str, Any] = Field(description="Logging configuration")
    myai: MyAiConfig = Field(description="MyAI bot configuration")

    webservice: WebServerConfig = Field(description="Web server configuration")
    hams: HamsConfig = Field(description="Health and monitoring configuration")
    events: EventConfig = Field(description="Process costs for events")

    model_config = {
        # secrets_dir='/run/secrets',
        "secrets_nested_subdir": True,
    }

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
