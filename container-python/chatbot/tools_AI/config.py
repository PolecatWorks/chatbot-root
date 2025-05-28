"""Configuration for tools package."""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import timedelta


class ToolLimits(BaseModel):
    """Configuration limits for a specific tool."""

    max_instances: int = Field(
        default=5, description="Maximum number of concurrent instances of this tool"
    )
    timeout: timedelta = Field(
        default=timedelta(seconds=30),
        description="Maximum time a tool can run before timing out",
    )
    enabled: bool = Field(default=True, description="Whether this tool is enabled")
    retry_count: int = Field(
        default=3, description="Number of times to retry the tool on failure"
    )
    retry_delay: timedelta = Field(
        default=timedelta(seconds=1), description="Delay between retries"
    )


class ToolConfig(BaseModel):
    """Configuration for tool execution."""

    default_max_instances: int = Field(
        default=5,
        description="Default maximum number of concurrent instances for tools",
    )
    default_timeout: timedelta = Field(
        default=timedelta(seconds=30), description="Default timeout for tools"
    )
    tool_configs: Dict[str, ToolLimits] = Field(
        default_factory=dict, description="Per-tool configuration"
    )
    enabled_tools: Dict[str, bool] = Field(
        default_factory=dict,
        description="Dictionary of tool names to enabled status. Missing tools default to enabled.",
    )
    instance_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Current count of running instances for each tool",
    )

    def get_tool_limits(self, tool_name: str) -> ToolLimits:
        """Get limits for a specific tool, using defaults if not configured."""
        if tool_name not in self.tool_configs:
            self.tool_configs[tool_name] = ToolLimits(
                max_instances=self.default_max_instances,
                timeout=self.default_timeout,
                enabled=self.enabled_tools.get(tool_name, True),
            )
        return self.tool_configs[tool_name]

    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a tool is enabled."""
        # First check explicit enabled_tools dict
        if tool_name in self.enabled_tools:
            return self.enabled_tools[tool_name]
        # Then check tool_configs if it exists
        if tool_name in self.tool_configs:
            return self.tool_configs[tool_name].enabled
        # Default to enabled
        return True

    def set_tool_enabled(self, tool_name: str, enabled: bool) -> None:
        """Enable or disable a tool."""
        self.enabled_tools[tool_name] = enabled
        if tool_name in self.tool_configs:
            self.tool_configs[tool_name].enabled = enabled
