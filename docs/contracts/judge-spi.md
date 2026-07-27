# Judge SPI + LLMClient 契约

> **Depends on**: ../architecture/design-principles.md, ./domain-model.md, ./metrics-definition.md
> **Referenced by**: ../phases/phase-1-foundation.md, ../phases/phase-4-judge.md, ../phases/phase-7-plugin.md
> **ADR**: 0004-llm-client-for-judge.md

## 1. 设计原则

- **LLMClient 与 AgentAdapter 分离**：AgentAdapter 面向被评测 Agent，LLMClient 面向系统内部 LLM 消费（Judge 等）
- **最小接口原则**：LLMClient 只提供单次 prompt → response 的调用，不涉及对话管理
- **Registry 统一模式**：LLMClient 和 Judge 均通过 Registry 注册，与 AdapterRegistry 模式一致
- **Open/Closed 原则**：新增 Judge / LLMClient 只需注册新实现，不修改已有代码

## 2. LLMClient 接口

### 2.1 LLMClient（MUST — 系统内部 LLM 调用统一接口）

```python
# judges/llm_client.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

class LLMClient(ABC):
    """系统内部 LLM 调用接口。
    用于 Judge 等系统组件调用 LLM，与 AgentAdapter 分离。
    AgentAdapter 面向被评测 Agent，LLMClient 面向系统内部 LLM 消费。"""

    @abstractmethod
    async def complete(self, prompt: str, *, model: str | None = None,
                       temperature: float = 0.0, max_tokens: int = 1024,
                       response_format: dict | None = None) -> "LLMResponse":
        """执行单次 LLM 调用，返回响应。"""
        pass

    @abstractmethod
    def validate_config(self, config: dict) -> bool:
        """校验 LLM Client 配置。"""
        pass

    @property
    @abstractmethod
    def provider(self) -> str:
        """LLM 提供商标识。"""
        pass
```

**MUST 约束**：
- `complete` 方法为单次调用，不维护对话历史
- `response_format` 为 `{"type": "json_object"}` 时，响应 `content` 必须为合法 JSON
- `temperature` 默认 0.0（Judge 场景需要确定性输出）
- `model` 为 None 时使用 Client 默认模型

### 2.2 LLMResponse（MUST）

```python
@dataclass
class LLMResponse:
    content: str                   # LLM 生成的文本
    model: str                     # 实际使用的模型名
    tokens: dict                   # {"prompt": N, "completion": M}
    finish_reason: str             # "stop" | "length" | "error"
    cost_usd: float                # 本次调用花费
```

### 2.3 LLMClientRegistry（MUST）

```python
class LLMClientRegistry(Registry[LLMClient]):
    """LLM Client 统一注册中心。"""
    pass
```

与 AdapterRegistry 使用相同的 Registry 基类。

## 3. Judge SPI

### 3.1 Judge 基础接口（MUST — 所有 Judge 必须实现）

```python
# judges/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

class Judge(ABC):
    """评测 Judge 基础接口。
    每个 Judge 负责评估一个或多个指标。"""

    @abstractmethod
    async def evaluate(self, ctx: "JudgeContext") -> "JudgeOutput":
        """执行评分，返回评分结果。"""
        pass

    @abstractmethod
    def validate_config(self, config: dict) -> bool:
        """校验 Judge 配置。"""
        pass

    @property
    @abstractmethod
    def judge_type(self) -> str:
        """Judge 类型标识。"""
        pass

    @property
    def supported_metrics(self) -> set[str]:
        """此 Judge 支持评估的指标集合。默认为空集。"""
        return set()
```

**MUST 约束**：
- `evaluate` 方法接收 `JudgeContext`，返回 `JudgeOutput`
- `supported_metrics` 声明此 Judge 能评估的指标标识集合
- JudgeService 根据 Scenario 配置的 metrics 列表匹配对应的 Judge

### 3.2 JudgeContext（MUST）

```python
@dataclass
class JudgeContext:
    scenario: Scenario             # 被评测的场景定义
    agent_execution: AgentExecution  # Agent 执行结果
    trace: Trace | None            # 执行 Trace（可选，部分 Judge 需要）
    config: dict                   # Judge 配置
    llm_client: LLMClient | None   # LLM Client（LLM Judge 使用）
```

### 3.3 JudgeOutput（MUST）

```python
@dataclass
class JudgeOutput:
    metric_scores: list[MetricScore]  # 指标评分列表
    reasoning: str                     # 评分理由（LLM Judge 填写）
    judge_type: str                    # 评分来源 Judge 类型
    metadata: dict                     # 附加元数据
```

### 3.4 JudgeRegistry（MUST）

```python
class JudgeRegistry(Registry[Judge]):
    """Judge 统一注册中心。"""
    pass
```

## 4. 内置 Judge 清单

| Judge | judge_type | supported_metrics | 说明 |
|-------|-----------|-------------------|------|
| RuleJudge | `rule` | `correctness`, `forbidden_check`, `tool_accuracy`, `intent_match` | 规则匹配评分 |
| LLMJudge | `llm` | `correctness`, `hallucination`, `planning_score`, `memory_accuracy`, `coherence` | LLM 评分 |
| EmbeddingJudge | `embedding` | `semantic_similarity`, `semantic_pass` | **MAY — MVP 不提供内置实现** |

### 4.1 RuleJudge（MUST — MVP 必须实现）

- 基于规则匹配评估指标
- 不依赖外部 LLM 调用
- 支持精确匹配、关键词检查、正则匹配、JSON 路径校验

### 4.2 LLMJudge（MUST — MVP 必须实现）

- 通过 `LLMClient` 调用 LLM 进行评分
- 使用 Prompt 模板生成评分请求
- 响应格式为 JSON，包含 score 和 reasoning
- `llm_client` 从 `JudgeContext` 获取

**MUST 约束**：
- LLMJudge 必须通过 `JudgeContext.llm_client` 获取 LLMClient 实例，不直接实例化 OpenAI 客户端
- LLMJudge 的 Prompt 模板必须支持配置覆盖
- LLMJudge 响应必须解析为 JSON，解析失败时记为 0 分并记录错误

### 4.3 EmbeddingJudge（MAY — 预留扩展点，MVP 不实现）

> **MAY**: EmbeddingJudge 接口为预留扩展点，MVP 不提供内置实现。
> 第三方可通过 Plugin 系统实现此接口并注册到 JudgeRegistry。
> `semantic_similarity` 和 `semantic_pass` 指标在 MVP 阶段默认无内置实现，
> 可由 LLM Judge 替代评估语义相似度。

```python
class EmbeddingJudge(Judge):
    """Embedding Judge — 预留扩展点，MVP 不实现。
    
    未来实现时通过 Embedding API 计算语义相似度。
    第三方可通过 Plugin 系统提供实现。"""
    pass
```

## 5. 内置 LLMClient 清单

| LLMClient | provider | MVP 状态 | 说明 |
|-----------|----------|----------|------|
| OpenAILLMClient | `openai` | MUST | OpenAI 兼容 API |
| AnthropicLLMClient | `anthropic` | MAY | Future Extension |
| LocalLLMClient | `local` | MAY | Future Extension |

### 5.1 OpenAILLMClient（MUST — MVP 必须实现）

- 调用 OpenAI 兼容 API
- 配置：`api_key_ref`, `base_url`, `default_model`
- 支持 `response_format={"type": "json_object"}` 强制 JSON 输出
- 通过 `LLMClientRegistry.register("openai", OpenAILLMClient)` 注册

## 6. JudgeService 调度逻辑

### 6.1 评分调度流程（MUST）

```python
async def judge_evaluation(self, evaluation_id: str):
    evaluation = await self.evaluation_repo.get(evaluation_id)
    
    for scenario_exec in evaluation.scenario_executions:
        agent_execution = scenario_exec.agent_execution
        scenario = scenario_exec.scenario
        
        # 获取场景配置的 metrics 列表
        configured_metrics = scenario.judge_config.get("metrics", [])
        
        # 根据 metrics 匹配 Judge
        judges = self._select_judges(configured_metrics)
        
        # 执行评分
        all_scores = []
        for judge in judges:
            ctx = JudgeContext(
                scenario=scenario,
                agent_execution=agent_execution,
                trace=agent_execution.trace,
                config=scenario.judge_config,
                llm_client=self.llm_client_registry.create(
                    scenario.judge_config.get("llm_provider", "openai"),
                    scenario.judge_config
                )
            )
            output = await judge.evaluate(ctx)
            all_scores.extend(output.metric_scores)
        
        # ScoreAggregator 加权聚合
        aggregated = self.score_aggregator.aggregate(all_scores, scenario.judge_config)
        
        # 保存 JudgeResult
        await self.judge_repo.save(JudgeResult(..., metric_scores=all_scores, ...))
```

### 6.2 Judge 选择逻辑（MUST）

- JudgeService 根据 `configured_metrics` 中每个指标匹配 `JudgeRegistry` 中 `supported_metrics` 包含该指标的 Judge
- 一个 Judge 可评估多个指标，一次 `evaluate` 调用返回多个 `MetricScore`
- 多个 Judge 可评估同一指标，ScoreAggregator 负责聚合
- 未注册任何 Judge 能评估的指标跳过并记录 warning

## 7. ScoreAggregator

### 7.1 加权聚合规则（MUST）

```python
class ScoreAggregator:
    def aggregate(self, scores: list[MetricScore], config: dict) -> AggregatedScore:
        """对指标评分进行加权聚合。"""
        weights = config.get("score_weights", {})
        total_weight = 0.0
        weighted_sum = 0.0
        
        for score in scores:
            weight = weights.get(score.metric_name, 1.0)
            weighted_sum += score.score * weight
            total_weight += weight
        
        final_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        return AggregatedScore(final_score=final_score, metric_scores=scores)
```

**MUST 约束**：
- 权重配置为可选，未配置时默认权重为 1.0（等权平均）
- 聚合基于实际产出的指标评分，不依赖固定指标列表
- 遵循 Open/Closed 原则：新增 Judge / 指标不需要修改 ScoreAggregator
