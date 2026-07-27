"""Dataset Replay: 使用旧 Dataset 对新 Agent 版本回放评测."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from agenteval.core.exceptions import NotFoundException

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class DatasetReplayService:
    """数据集回放服务.

    简化策略: 复用同一 Dataset + 新 AgentConfig 重新触发 Evaluation，
    不引入变量控制/流量分配等复杂抽象。
    """

    def __init__(self, session: AsyncSession):
        """初始化.

        Args:
            session: 数据库会话
        """
        self.session = session

    async def replay(
        self,
        baseline_evaluation_id: UUID,
        new_agent_config: dict,
        name: str | None = None,
    ) -> UUID:
        """使用基线评测的 Dataset + 新 Agent 配置创建新评测.

        Args:
            baseline_evaluation_id: 基线评测 ID
            new_agent_config: 新的 Agent 配置
            name: 新评测名称（可选）

        Returns:
            新 Evaluation ID

        Raises:
            NotFoundException: 基线评测不存在
        """
        from agenteval.infra.repositories.evaluation_repo import EvaluationRepository
        from agenteval.schemas.evaluation import CreateEvaluationRequest
        from agenteval.services.evaluation_service import EvaluationService

        eval_repo = EvaluationRepository(self.session)
        baseline = await eval_repo.get_by_id(baseline_evaluation_id)

        if not baseline:
            raise NotFoundException("Evaluation", str(baseline_evaluation_id))

        # 构建新评测请求
        eval_name = name or f"Replay-{baseline.name}-{datetime.now().strftime('%Y%m%d%H%M')}"

        create_request = CreateEvaluationRequest(
            name=eval_name,
            dataset_id=baseline.dataset_id,
            agent_config=new_agent_config,
            judge_configs=baseline.judge_configs or [],
            version_label=f"replay-of-{baseline.version_label or str(baseline.id)[:8]}",
            config=baseline.config or {},
        )

        # 创建新评测
        eval_service = EvaluationService(self.session)
        new_eval = await eval_service.create_evaluation(baseline.project_id, create_request)

        return new_eval.id
