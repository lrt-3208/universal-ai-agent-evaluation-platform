"""Plugin SPI interfaces.

Reference: ../docs/phases/phase-7-plugin.md §5
"""

from agenteval.plugins.spi.judge_plugin import JudgePlugin
from agenteval.plugins.spi.adapter_plugin import AdapterPlugin
from agenteval.plugins.spi.dataset_plugin import DatasetPlugin
from agenteval.plugins.spi.metrics_plugin import MetricsPlugin, MetricDefinition
from agenteval.plugins.spi.report_plugin import ReportPlugin

__all__ = [
    "JudgePlugin",
    "AdapterPlugin",
    "DatasetPlugin",
    "MetricsPlugin",
    "MetricDefinition",
    "ReportPlugin",
]
