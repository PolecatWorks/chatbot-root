from datetime import timedelta
from typing import List
from pydantic import BaseModel, Field


class ToolConfig(BaseModel):
    """Configuration for tool execution."""

    name: str = Field(
        description="Name of the tool, used to identify it in the system"
    )

    max_instances: int = Field(
        default=5,
        description="Default maximum number of concurrent instances for tools",
    )
    timeout: timedelta = Field(
        default=timedelta(seconds=30), description="Default timeout for tools"
    )
    # tool_configs: Dict[str, ToolLimits] = Field(
    #     default_factory=dict,
    #     description="Per-tool configuration"
    # )
    instance_counts: int = Field(
        default=5,
        description="Current count of running instances for each tool",
    )


class ToolBoxConfig(BaseModel):
    """Configuration for tool execution."""

    tools: List[ToolConfig] = Field(
        description="Per-tool configuration with default settings"
    )
    max_concurrent: int = Field(
        description="Default maximum number of concurrent instances for tools"
    )
