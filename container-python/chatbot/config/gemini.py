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
    model: str = Field(
        description="The model to use for the bot, e.g., 'gemini-1.5-flash'",
    )
    max_output_tokens: int = Field(
        description="Maximum number of output tokens for the bot's response",
    )
    temperature: float = Field(
        description="Temperature for the bot's response generation, controlling randomness",
    )
