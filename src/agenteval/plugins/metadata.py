"""Plugin metadata dataclass.

Reference: ../docs/phases/phase-7-plugin.md §4.2
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PluginMetadata:
    """插件元数据（从 plugin.toml 解析）."""

    name: str
    version: str
    type: str  # judge | adapter | dataset | metrics | report
    entry_point: str  # module:ClassName
    author: str | None = None
    description: str | None = None
    min_agenteval_version: str | None = None
    config_schema: str = "{}"  # JSON Schema string
    dependencies: dict = field(default_factory=dict)
    manifest_path: str | None = None
    security: dict = field(default_factory=dict)
