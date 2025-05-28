from .tool import ToolBoxConfig, ToolConfig
from pydantic import Field, BaseModel
from chatbot.hams.config import HamsConfig
from pydantic import Field, BaseModel, SecretStr
from pydantic import HttpUrl
from pydantic_settings import BaseSettings, YamlConfigSettingsSource, SettingsConfigDict
from pydantic_file_secrets import FileSecretsSettingsSource
from pathlib import Path
from typing import Dict, Any, List, Self
from datetime import timedelta
from chatbot.config.gemini import GeminiConfig, GeminiPart

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



class MyAiConfig(BaseModel):
    """
    Configuration for the MyAI bot
    """

    model: str = Field(
        # default="gemini-1.5-flash",
        description="The model to use for the bot, e.g., 'gemini-1.5-flash'",
    )

    system_instruction: List[GeminiPart] = Field(
        description="List of system instructions for the bot",
    )

    max_output_tokens: int = Field(
        description="Maximum number of output tokens for the bot's response",
    )

    temperature: float = Field(
        description="Temperature for the bot's response generation, controlling randomness",
    )
    toolbox: ToolBoxConfig = Field(
        description="Default configuration for tool execution, including limits and enabled status",
    )


class ServiceConfig(BaseSettings):
    """
    Configuration for the service
    """

    logging: Dict[str, Any] = Field(description="Logging configuration")
    bot: BotConfig = Field(description="Bot configuration")
    gemini: GeminiConfig = Field(description="Gemini configuration")
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
