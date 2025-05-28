from typing import List
from pydantic import Field, BaseModel, SecretStr


class GeminiPart(BaseModel):
    """
    Configuration for a part of the bot
    """

    text: str = Field(
        description="Instruction text for the part, e.g., 'You are a helpful assistant.'",
    )


class GeminiConfig(BaseModel):
    """
    Configuration for the bot
    """

    gcp_llm_key: SecretStr = Field(
        description="Google Cloud Platform LLM API key",
    )
