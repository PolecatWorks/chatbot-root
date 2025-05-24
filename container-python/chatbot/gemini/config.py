from pydantic import Field, BaseModel, SecretStr


class GeminiConfig(BaseModel):
    """
    Configuration for the bot
    """

    gcp_llm_key: SecretStr = Field(
        description="Google Cloud Platform LLM API key",
    )

    model: str = Field(
        # default="gemini-1.5-flash",
        description="The model to use for the bot, e.g., 'gemini-1.5-flash'",
    )
