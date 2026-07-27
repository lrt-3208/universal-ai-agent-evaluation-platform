"""Regression Service: 回归分析主服务."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from agenteval.core.exceptions import ConflictException, NotFoundException
from agenteval.services.regression.flaky_detector import FlakyDetector
from agenteval.services.regression.regression_analyzer import RegressionAnalyzer
from agenteval.services.regression.scenario_matcher import ScenarioMatcher
from agenteval.services.regression.score_differ import RegressionVerdict, ScoreDiffer

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from agenteval.infra.models.evaluation_model import EvaluationModel
    from agenteval.infra.models.regression_model import RegressionModel
    from agenteval.schemas.regression import CreateRegressionRequest


class RegressionService:
    """回归分析服务.

    编排 ScenarioMatcher、ScoreDiffer、RegressionAnalyzer 完成回归分析。
    """

    def __init__(self, session: AsyncSession):
        """初始化.

        Args:
            session: 数据库会话
        """
        self.session = session
        self.matcher = ScenarioMatcher()
        self.differ = ScoreDiffer()
        self.analyzer = RegressionAnalyzer()

    async def create_regression(
        self,
        request: CreateRegressionRequest,
        project_id: UUID,
    ) -> RegressionModel:
        """创建并执行回归分析.

        Args:
            request: 创建请求
            project_id: 项目 ID

        Returns:
            Regression 实体

        Raises:
            NotFoundException: 评测不存在
            AgentEvalException: 评测未完成或 Dataset 不一致
        """
        from agenteval.infra.models.regression_model import RegressionModel
        from agenteval.infra.repositories.evaluation_repo import EvaluationRepository

        eval_repo = EvaluationRepository(self.session)

        # 加载两个评测
        baseline = await eval_repo.get_by_id(request.baseline_evaluation_id)
        target = await eval_repo.get_by_id(request.target_evaluation_id)

        self._validate(baseline, target)

        # 创建 Regression 实体
        regression = RegressionModel(
            id=uuid4(),
            project_id=project_id,
            name=request.name,
            baseline_evaluation_id=request.baseline_evaluation_id,
            target_evaluation_id=request.target_evaluation_id,
            status="analyzing",
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(regression)
        await self.session.flush()

        # 执行分析
        try:
            result = await self._analyze(baseline, target, request)
            regression.scenario_diffs = [d.to_dict() for d in result.scenario_diffs]
            regression.metric_diffs = result.metric_diffs
            regression.overall_verdict = result.overall_verdict
            regression.summary = result.summary
            regression.status = "completed"
            regression.completed_at = datetime.now(timezone.utc)
        except Exception as e:
            regression.status = "failed"
            regression.error_message = str(e)
            await self.session.flush()
            raise

        await self.session.flush()
        return regression

    async def _analyze(
        self,
        baseline: EvaluationModel,
        target: EvaluationModel,
        request: CreateRegressionRequest,
    ):
        """执行回归分析."""
        from agenteval.infra.repositories.execution_repo import ScenarioExecutionRepository
        from agenteval.infra.repositories.judge_result_repo import JudgeResultRepository
        from agenteval.infra.repositories.scenario_repo import ScenarioRepository
        from agenteval.services.regression.regression_analyzer import RegressionAnalysis

        exec_repo = ScenarioExecutionRepository(self.session)
        judge_repo = JudgeResultRepository(self.session)
        scenario_repo = ScenarioRepository(self.session)

        baseline_execs = await exec_repo.list_by_evaluation(baseline.id)
        target_execs = await exec_repo.list_by_evaluation(target.id)

        # 预加载 judge_results 和 scenario 以避免懒加载
        # 使用 object.__setattr__ 避免触发 ORM 的 attribute setter
        for exec_model in baseline_execs + target_execs:
            # 加载 judge results
            judge_results = await judge_repo.list_by_scenario_execution(exec_model.id)
            object.__setattr__(exec_model, "_loaded_judge_results", judge_results)
            # 加载 scenario
            scenario = await scenario_repo.get_by_id(exec_model.scenario_id)
            object.__setattr__(exec_model, "_loaded_scenario", scenario)

        # 匹配场景
        pairs = self.matcher.match(baseline_execs, target_execs)

        # 配置 differ
        self.differ.threshold = request.regression_threshold

        # 计算差异
        metrics_filter = request.metrics_filter if request.metrics_filter else None
        scenario_diffs = self.differ.diff(pairs, metrics_filter)

        # Flaky 检测（可选）
        if request.flaky_window > 0:
            history = await self._load_history(baseline.project_id, request.flaky_window)
            detector = FlakyDetector()
            flaky_ids = detector.detect(history)
            for diff in scenario_diffs:
                if diff.scenario_id in flaky_ids:
                    diff.verdict = RegressionVerdict.FLAKY.value

        # 计算指标级差异
        metric_diffs = self.analyzer.compute_metric_diffs(scenario_diffs)

        # 填充 baseline/target 均值
        metric_diffs = self._fill_metric_means(metric_diffs, baseline_execs, target_execs)

        # 分析总体结论
        return self.analyzer.analyze(scenario_diffs, metric_diffs)

    def _validate(self, baseline: EvaluationModel | None, target: EvaluationModel | None):
        """校验评测有效性."""
        if not baseline:
            raise NotFoundException("Evaluation", "baseline")
        if not target:
            raise NotFoundException("Evaluation", "target")
        if baseline.status != "completed":
            raise ConflictException("Baseline evaluation not completed")
        if target.status != "completed":
            raise ConflictException("Target evaluation not completed")
        if baseline.dataset_id != target.dataset_id:
            raise ConflictException(
                "Baseline and target evaluations must use the same dataset"
            )

    async def _load_history(
        self,
        project_id: UUID,
        window: int,
    ) -> dict[UUID, list]:
        """加载历史评测数据用于 Flaky 检测."""
        from agenteval.infra.repositories.evaluation_repo import EvaluationRepository
        from agenteval.infra.repositories.execution_repo import ScenarioExecutionRepository

        eval_repo = EvaluationRepository(self.session)
        exec_repo = ScenarioExecutionRepository(self.session)

        # 获取最近 N 次已完成的评测
        evaluations = await eval_repo.list_by_project(project_id, limit=window + 5)
        completed = [e for e in evaluations if e.status == "completed"][:window]

        # 收集每个场景的历史执行
        history: dict[UUID, list] = {}
        for eval_model in completed:
            execs = await exec_repo.list_by_evaluation(eval_model.id)
            for exec_model in execs:
                history.setdefault(exec_model.scenario_id, []).append(exec_model)

        return history

    def _fill_metric_means(
        self,
        metric_diffs: dict,
        baseline_execs: list,
        target_execs: list,
    ) -> dict:
        """填充指标的 baseline/target 均值."""
        baseline_scores = self._collect_metric_scores(baseline_execs)
        target_scores = self._collect_metric_scores(target_execs)

        for key, diff in metric_diffs.items():
            b_scores = baseline_scores.get(key, [])
            t_scores = target_scores.get(key, [])
            diff["baseline_mean"] = round(sum(b_scores) / len(b_scores), 4) if b_scores else None
            diff["target_mean"] = round(sum(t_scores) / len(t_scores), 4) if t_scores else None

        return metric_diffs

    def _collect_metric_scores(self, execs: list) -> dict[str, list[float]]:
        """收集所有执行的指标得分."""
        scores: dict[str, list[float]] = {}
        for exec_model in execs:
            # judge_results 是预加载的属性
            judge_results = getattr(exec_model, "_loaded_judge_results", None)
            if not judge_results:
                continue
            for jr in judge_results:
                if jr.status != "completed":
                    continue
                # metric_scores 是 JSONB list，每个元素是 dict
                for ms in jr.metric_scores:
                    metric_key = ms.get("metric_key", "") if isinstance(ms, dict) else getattr(ms, "metric_key", "")
                    score = ms.get("score", 0.0) if isinstance(ms, dict) else getattr(ms, "score", 0.0)
                    if metric_key:
                        scores.setdefault(metric_key, []).append(score)
        return scores
