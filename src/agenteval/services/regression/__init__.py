"""Regression analysis services."""

from agenteval.services.regression.scenario_matcher import ScenarioMatcher
from agenteval.services.regression.score_differ import ScoreDiffer, ScenarioDiff
from agenteval.services.regression.regression_analyzer import RegressionAnalyzer, RegressionAnalysis
from agenteval.services.regression.flaky_detector import FlakyDetector
from agenteval.services.regression.dataset_replay import DatasetReplayService
from agenteval.services.regression.regression_service import RegressionService
from agenteval.services.regression.diff_report_generator import DiffReportGenerator, RegressionReportData

__all__ = [
    "ScenarioMatcher",
    "ScoreDiffer",
    "ScenarioDiff",
    "RegressionAnalyzer",
    "RegressionAnalysis",
    "FlakyDetector",
    "DatasetReplayService",
    "RegressionService",
    "DiffReportGenerator",
    "RegressionReportData",
]
