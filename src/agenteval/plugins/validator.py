"""Plugin validator.

Reference: ../docs/phases/phase-7-plugin.md §6.3
"""

from __future__ import annotations

from agenteval.plugins.metadata import PluginMetadata


class PluginValidator:
    """插件合规性校验."""

    REQUIRED_MANIFEST_FIELDS = ["name", "version", "type", "entry_point"]
    VALID_TYPES = ["judge", "adapter", "dataset", "metrics", "report"]

    def validate(self, metadata: PluginMetadata) -> list[str]:
        """校验插件元数据.

        Args:
            metadata: 插件元数据

        Returns:
            错误列表，空列表表示通过
        """
        errors = []

        # 必填字段
        for field_name in self.REQUIRED_MANIFEST_FIELDS:
            if not getattr(metadata, field_name, None):
                errors.append(f"Missing required field: {field_name}")

        # 类型校验
        if metadata.type and metadata.type not in self.VALID_TYPES:
            errors.append(f"Invalid plugin type: {metadata.type}. Valid: {self.VALID_TYPES}")

        # entry_point 格式
        if metadata.entry_point and ":" not in metadata.entry_point:
            errors.append("entry_point must be 'module:ClassName' format")

        # 版本格式
        if metadata.version:
            try:
                parts = metadata.version.split(".")
                if len(parts) < 2:
                    raise ValueError("too few parts")
                tuple(int(x) for x in parts)
            except ValueError:
                errors.append(f"Invalid version format: {metadata.version}")

        return errors
