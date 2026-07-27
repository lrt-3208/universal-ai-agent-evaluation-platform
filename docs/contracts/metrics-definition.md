# Metrics Definition — 评测指标体系

> **Depends on**: `domain-model.md`, `judge-spi.md`  
> **Referenced by**: `../phases/phase-4-judge.md`, `../phases/phase-5-report.md`, `../phases/phase-6-regression.md`  
> **ADR**: 无

## 1. 目标

定义 AgentEval 的评测指标体系。指标定义保持稳定，使用 **Recommended** 分类而非固定“MVP 必做列表”——指标本身无 MVP/Post-MVP 之分，只有对应 Judge 实现有优先级。

### 指标 MVP 状态标注

| 状态 | 含义 |
|--------|------|
| Recommended - Core | 建议优先实现，覆盖核心质量维度 |
| Recommended - Extended | 建议扩展实现，覆盖能力/性能/成本维度 |
| Optional | 待 Embedding Judge (MAY) 启用后可用 |

## 2. 指标体系总览

### 2.1 指标分类

| 类别 | 指标 | 说明 | 推荐状态 |
|------|------|------|----------|
| 质量 | Correctness | 回答正确性 | Recommended - Core |
| 质量 | Hallucination | 幻觉率（越低越好，分数越高越好） | Recommended - Core |
| 能力 | Tool Accuracy | 工具调用准确率 | Recommended - Core |
| 能力 | Memory Accuracy | 记忆使用准确率 | Recommended - Extended |
| 能力 | Planning Score | 多步规划质量 | Recommended - Extended |
| 性能 | Latency | 响应延迟 | Recommended - Core |
| 成本 | Cost | 单次调用花费 | Recommended - Extended |
| 辅助 | Coherence | 回答连贯性 | Recommended - Extended |
| 辅助 | Intent Match | 意图匹配度 | Recommended - Core |
| 辅助 | Semantic Similarity | 语义相似度 | Optional |
| 辅助 | Forbidden Check | 禁止内容检查 | Recommended - Core |

### 2.2 指标与 Judge 映射

| 指标 | Rule Judge | LLM Judge | Embedding Judge | Trace-derived |
|------|:---------:|:---------:|:--------------:|:-------------:|
| Correctness | ✓ | ✓ | - | - |
| Hallucination | - | ✓ | - | - |
| Tool Accuracy | ✓ | ✓ | - | ✓ |
| Memory Accuracy | ✓ | ✓ | - | - |
| Planning Score | - | ✓ | - | ✓ |
| Latency | - | - | - | ✓ |
| Cost | - | - | - | ✓ |
| Coherence | - | ✓ | - | - |
| Intent Match | ✓ | ✓ | - | - |
| Semantic Similarity | - | - | ✓ | - |
| Forbidden Check | ✓ | - | - | - |

## 3. 指标详细定义

### 3.1 Correctness（正确性）

| 属性 | 值 |
|------|-----|
| 指标键 | `correctness` |
| 显示名 | Correctness |
| 取值范围 | [0.0, 1.0] |
| 默认权重 | 1.0 |
| 方向 | higher_is_better |
| 适用 Judge | Rule, LLM |

**Rule Judge 计算方式：**

```
correctness = matched_keywords / total_expected_keywords

其中:
  matched_keywords = 命中 response_contains 的关键词数
  total_expected_keywords = response_contains 列表长度

若 response_contains 为空，correctness = 1.0（无约束视为通过）
```

**LLM Judge 计算方式：**

```
LLM 收到 scenario.expected.reference_answer 和 agent_response，
输出 0.0-1.0 的分数。

评分标准:
  1.0 = 与参考答案完全一致或等价
  0.8 = 核心信息正确，细节有差异
  0.5 = 部分正确，存在遗漏或不准确
  0.2 = 基本不正确，但尝试回答了
  0.0 = 完全错误或未回答
```

### 3.2 Hallucination（幻觉率）

| 属性 | 值 |
|------|-----|
| 指标键 | `hallucination` |
| 显示名 | Hallucination |
| 取值范围 | [0.0, 1.0] |
| 默认权重 | 2.0 |
| 方向 | higher_is_better（1.0 = 无幻觉） |
| 适用 Judge | LLM |

**计算方式：**

```
hallucination_score = 1.0 - hallucination_rate

其中 hallucination_rate 由 LLM 判定:
  LLM 分析 agent_response 中是否存在:
    1. 编造的事实信息
    2. 不存在的实体/事件引用
    3. 与已知事实矛盾的陈述
    4. 虚构的工具调用结果

评分标准:
  1.0 = 无任何幻觉
  0.8 = 轻微不确定表述，但无编造
  0.5 = 存在部分编造内容
  0.2 = 大量编造内容
  0.0 = 完全编造
```

**LLM Prompt 指令：**

```
Evaluate if the agent's response contains hallucinated content.
Hallucination includes: fabricated facts, non-existent entities,
contradictory statements, or invented tool results.
Score 1.0 = no hallucination, 0.0 = severe hallucination.
```

### 3.3 Tool Accuracy（工具调用准确率）

| 属性 | 值 |
|------|-----|
| 指标键 | `tool_accuracy` |
| 显示名 | Tool Accuracy |
| 取值范围 | [0.0, 1.0] |
| 默认权重 | 1.5 |
| 方向 | higher_is_better |
| 适用 Judge | Rule, LLM, Trace-derived |

**Rule Judge 计算方式：**

```
tool_accuracy = matched_tool_calls / total_expected_tool_calls

其中:
  matched_tool_calls = tool_calls_expected 中被匹配的数量
  匹配条件:
    1. tool_name 一致
    2. args_match 中指定的参数值一致（部分匹配）
  total_expected_tool_calls = tool_calls_expected 列表长度

若 tool_calls_expected 为空，tool_accuracy = 1.0
```

**Trace-derived 计算方式：**

```
tool_accuracy = successful_tool_calls / total_tool_calls

其中:
  successful_tool_calls = Trace 中 status="ok" 的 tool_call span 数
  total_tool_calls = Trace 中所有 tool_call span 数

此计算不依赖 expected，反映 Agent 工具调用的成功率。
```

**LLM Judge 计算方式：**

```
LLM 评估工具选择的合理性和参数准确性:
  1.0 = 工具选择正确，参数完全准确
  0.8 = 工具选择正确，参数有小误差
  0.5 = 工具选择部分正确
  0.2 = 工具选择错误
  0.0 = 未调用必要工具或调用了错误工具
```

### 3.4 Memory Accuracy（记忆使用准确率）

| 属性 | 值 |
|------|-----|
| 指标键 | `memory_accuracy` |
| 显示名 | Memory Accuracy |
| 取值范围 | [0.0, 1.0] |
| 默认权重 | 1.0 |
| 方向 | higher_is_better |
| 适用 Judge | Rule, LLM |

**Rule Judge 计算方式：**

```
memory_accuracy = correctly_used_memory_keys / total_memory_keys

其中:
  correctly_used_memory_keys = 在 response 中体现的 memory key 数
  total_memory_keys = scenario.memory.long_term + working 的 key 数

检测方式: 对每个 memory key，检查 response 中是否正确引用了该值。
  例: memory.long_term = {user_name: "张三"}
      response 包含 "张三" → correctly_used +1
```

**LLM Judge 计算方式：**

```
LLM 评估 Agent 是否正确使用了提供的记忆:
  1.0 = 所有记忆正确使用
  0.8 = 大部分记忆正确使用
  0.5 = 部分记忆使用正确
  0.2 = 记忆使用基本错误
  0.0 = 完全忽略记忆或错误使用

若无 memory 提供，memory_accuracy = 1.0
```

### 3.5 Planning Score（规划质量）

| 属性 | 值 |
|------|-----|
| 指标键 | `planning_score` |
| 显示名 | Planning Score |
| 取值范围 | [0.0, 1.0] |
| 默认权重 | 1.0 |
| 方向 | higher_is_better |
| 适用 Judge | LLM, Trace-derived |

**LLM Judge 计算方式：**

```
LLM 评估 Agent 的多步推理和规划质量:
  1.0 = 规划合理，步骤有序，无冗余
  0.8 = 规划基本合理，有小瑕疵
  0.5 = 规划存在明显问题（遗漏步骤/冗余步骤）
  0.2 = 规划混乱
  0.0 = 无规划或规划完全错误

若无多步推理需求（单轮直接回答），planning_score = 1.0
```

**Trace-derived 计算方式：**

```
planning_score 基于以下因素:
  1. 推理步骤数 vs 期望步骤数 (expected_plan 长度)
  2. 工具调用顺序合理性
  3. 无回溯（重复调用相同工具相同参数）

  若存在 expected_plan:
    step_match_ratio = matched_steps / len(expected_plan)
    planning_score = step_match_ratio * 0.7 + order_score * 0.3

  若不存在 expected_plan:
    仅基于 Trace 中 reasoning span 的质量评估
```

### 3.6 Latency（响应延迟）

| 属性 | 值 |
|------|-----|
| 指标键 | `latency` |
| 显示名 | Latency |
| 取值范围 | [0.0, 1.0] |
| 默认权重 | 0.5 |
| 方向 | higher_is_better（分数越高=延迟越低） |
| 适用 Judge | Trace-derived |

**计算方式：**

```
latency_score = max(0.0, 1.0 - (actual_latency_ms / max_latency_ms))

其中:
  actual_latency_ms = AgentExecution.latency_ms
  max_latency_ms = scenario.constraints.max_latency_ms (默认 10000)

分段评分:
  actual <= max * 0.3  → 1.0
  actual <= max * 0.5  → 0.8
  actual <= max * 0.8  → 0.5
  actual <= max        → 0.2
  actual > max         → 0.0

公式:
  if actual <= max * 0.3: score = 1.0
  elif actual <= max: score = 1.0 - 0.8 * (actual - max*0.3) / (max*0.7)
  else: score = 0.0
```

### 3.7 Cost（调用花费）

| 属性 | 值 |
|------|-----|
| 指标键 | `cost` |
| 显示名 | Cost |
| 取值范围 | [0.0, 1.0] |
| 默认权重 | 0.3 |
| 方向 | higher_is_better（分数越高=花费越低） |
| 适用 Judge | Trace-derived |

**计算方式：**

```
cost_score = max(0.0, 1.0 - (actual_cost / max_cost))

其中:
  actual_cost = AgentExecution.cost_usd
  max_cost = scenario.constraints.max_cost_usd (默认 0.05)

分段评分:
  actual <= max * 0.2  → 1.0
  actual <= max * 0.5  → 0.8
  actual <= max        → 0.5
  actual > max         → 0.0
```

### 3.8 Coherence（连贯性）

| 属性 | 值 |
|------|-----|
| 指标键 | `coherence` |
| 显示名 | Coherence |
| 取值范围 | [0.0, 1.0] |
| 默认权重 | 0.5 |
| 方向 | higher_is_better |
| 适用 Judge | LLM |

**计算方式：**

```
LLM 评估回复的连贯性和可读性:
  1.0 = 结构清晰，逻辑连贯，语言流畅
  0.8 = 基本连贯，有小瑕疵
  0.5 = 连贯性一般，存在跳跃
  0.2 = 连贯性差，难以理解
  0.0 = 完全不连贯
```

### 3.9 Intent Match（意图匹配）

| 属性 | 值 |
|------|-----|
| 指标键 | `intent_match` |
| 显示名 | Intent Match |
| 取值范围 | [0.0, 1.0]（二值：0.0 或 1.0） |
| 默认权重 | 1.0 |
| 方向 | higher_is_better |
| 适用 Judge | Rule, LLM |

**Rule Judge 计算方式：**

```
intent_match = 1.0 if intent_detected else 0.0

检测: 基于 expected.intent 在预定义关键词映射表中查找关键词，
      检查 response 中是否包含任一关键词。

预设意图关键词映射:
  weather_query: [天气, weather, 气温]
  search: [搜索, 查找, search, find]
  booking: [预订, 预约, book, reserve]
  calculation: [计算, 等于, calculate, result]
  translation: [翻译, translate]
  summarization: [总结, 摘要, summary]
  coding: [代码, 编程, code, function]
```

### 3.10 Semantic Similarity（语义相似度）

| 属性 | 值 |
|------|-----|
| 指标键 | `semantic_similarity` |
| 显示名 | Semantic Similarity |
| 取值范围 | [0.0, 1.0] |
| 默认权重 | 1.0 |
| 方向 | higher_is_better |
| 适用 Judge | Embedding |

**计算方式：**

```
semantic_similarity = cosine_similarity(embed(response), embed(reference))

其中:
  embed(x) = 使用 embedding 模型获取向量
  cosine_similarity(a, b) = dot(a, b) / (|a| * |b|)

要求 scenario.expected.reference_answer 存在，否则跳过。
```

### 3.11 Forbidden Check（禁止内容检查）

| 属性 | 值 |
|------|-----|
| 指标键 | `forbidden_check` |
| 显示名 | Forbidden Check |
| 取值范围 | [0.0, 1.0]（二值） |
| 默认权重 | 0.5 |
| 方向 | higher_is_better（1.0 = 无违规） |
| 适用 Judge | Rule |

**计算方式：**

```
forbidden_check = 0.0 if any_violation else 1.0

检查项:
  1. response_not_contains: response 中是否包含禁止关键词
  2. forbidden_patterns: response 中是否匹配禁止正则
  3. must_not_use_tools: Trace 中是否调用了禁止工具

任一检查项违规 → forbidden_check = 0.0
全部通过 → forbidden_check = 1.0
```

### 3.12 Semantic Pass（语义达标）

| 属性 | 值 |
|------|-----|
| 指标键 | `semantic_pass` |
| 显示名 | Semantic Pass |
| 取值范围 | [0.0, 1.0]（二值） |
| 默认权重 | 0.5 |
| 方向 | higher_is_better |
| 适用 Judge | Embedding |

**计算方式：**

```
semantic_pass = 1.0 if semantic_similarity >= threshold else 0.0

默认 threshold = 0.75（可通过 EmbeddingJudgeParams.threshold 配置）
```

## 4. 指标聚合规则

### 4.1 场景级聚合

单个 ScenarioExecution 的 overall_score 计算：

```
overall_score = Σ(metric_score * metric_weight) / Σ(metric_weight)

约束:
  - 所有 metric_score 已归一化到 [0.0, 1.0]
  - metric_weight 来自 judge_config.weights 或默认值
  - 同一 metric_key 多个 Judge 时取加权平均

overall_verdict:
  overall_score >= 0.8 → "pass"
  overall_score >= 0.5 → "partial"
  overall_score < 0.5 → "fail"
```

### 4.2 评测级聚合

Evaluation 级别的 Metrics 聚合：

```
对每个 metric_key:
  mean   = 平均值
  std    = 标准差
  min    = 最小值
  max    = 最大值
  p50    = 中位数
  p95    = 95 百分位
  histogram = [0-0.1, 0.1-0.2, ..., 0.9-1.0] 的分布

评测级 pass_rate:
  pass_rate = count(overall_score >= 0.8) / total_scored_scenarios

评测级 overall_score:
  evaluation_score = mean(all_scenario_overall_scores)
```

### 4.3 聚合示例

```
Scenario S001:
  Rule Judge:
    correctness: 1.0 (weight=1.0)
    tool_accuracy: 0.5 (weight=1.5)
    forbidden_check: 1.0 (weight=0.5)
    intent_match: 1.0 (weight=1.0)
  LLM Judge:
    correctness: 0.9 (weight=1.0)
    hallucination: 0.85 (weight=2.0)
    coherence: 0.95 (weight=0.5)
    planning_score: 0.8 (weight=1.0)
  Embedding Judge:
    semantic_similarity: 0.78 (weight=1.0)
    semantic_pass: 1.0 (weight=0.5)
  Trace-derived:
    latency: 0.6 (weight=0.5)
    cost: 0.8 (weight=0.3)

指标级加权平均:
  correctness: (1.0*1.0 + 0.9*1.0) / 2.0 = 0.95  (weight=1.0)
  tool_accuracy: 0.5  (weight=1.5)
  forbidden_check: 1.0  (weight=0.5)
  intent_match: 1.0  (weight=1.0)
  hallucination: 0.85  (weight=2.0)
  coherence: 0.95  (weight=0.5)
  planning_score: 0.8  (weight=1.0)
  semantic_similarity: 0.78  (weight=1.0)
  semantic_pass: 1.0  (weight=0.5)
  latency: 0.6  (weight=0.5)
  cost: 0.8  (weight=0.3)

overall_score = (0.95*1.0 + 0.5*1.5 + 1.0*0.5 + 1.0*1.0 + 0.85*2.0
                + 0.95*0.5 + 0.8*1.0 + 0.78*1.0 + 1.0*0.5 + 0.6*0.5 + 0.8*0.3)
              / (1.0+1.5+0.5+1.0+2.0+0.5+1.0+1.0+0.5+0.5+0.3)
              = 7.939 / 9.8
              = 0.8101
overall_verdict = "pass" (>= 0.8)
```

## 5. 指标定义注册表

### 5.1 MetricDefinition 结构

```python
# domain/value_objects/metric_unit.py
from dataclasses import dataclass

@dataclass
class MetricDefinition:
    key: str
    name: str
    description: str
    score_range: tuple[float, float]
    default_weight: float
    higher_is_better: bool
    applicable_judges: list[str]
    calculation_method: str  # 计算方式描述
    requires_expected: bool  # 是否需要 scenario.expected 字段
    requires_trace: bool     # 是否需要 Trace 数据
```

### 5.2 内置指标注册表

```python
# domain/metric_registry.py
class MetricRegistry:
    _definitions: dict[str, MetricDefinition] = {}

    @classmethod
    def register(cls, definition: MetricDefinition):
        cls._definitions[definition.key] = definition

    @classmethod
    def get(cls, key: str) -> MetricDefinition | None:
        return cls._definitions.get(key)

    @classmethod
    def all_keys(cls) -> list[str]:
        return list(cls._definitions.keys())

    @classmethod
    def by_judge_type(cls, judge_type: str) -> list[str]:
        return [k for k, d in cls._definitions.items()
                if judge_type in d.applicable_judges]

# 注册内置指标
MetricRegistry.register(MetricDefinition(
    key="correctness", name="Correctness",
    description="Response correctness against expected output",
    score_range=(0.0, 1.0), default_weight=1.0, higher_is_better=True,
    applicable_judges=["rule", "llm"],
    calculation_method="keyword_match or llm_eval",
    requires_expected=True, requires_trace=False))

MetricRegistry.register(MetricDefinition(
    key="hallucination", name="Hallucination",
    description="Absence of hallucinated content (1.0 = no hallucination)",
    score_range=(0.0, 1.0), default_weight=2.0, higher_is_better=True,
    applicable_judges=["llm"],
    calculation_method="llm_eval",
    requires_expected=False, requires_trace=False))

MetricRegistry.register(MetricDefinition(
    key="tool_accuracy", name="Tool Accuracy",
    description="Accuracy of tool calls compared to expected",
    score_range=(0.0, 1.0), default_weight=1.5, higher_is_better=True,
    applicable_judges=["rule", "llm", "trace"],
    calculation_method="matched_calls/expected_calls or trace_success_rate",
    requires_expected=True, requires_trace=False))

MetricRegistry.register(MetricDefinition(
    key="memory_accuracy", name="Memory Accuracy",
    description="Correct usage of provided memory/context",
    score_range=(0.0, 1.0), default_weight=1.0, higher_is_better=True,
    applicable_judges=["rule", "llm"],
    calculation_method="used_memory_keys/total_keys or llm_eval",
    requires_expected=False, requires_trace=False))

MetricRegistry.register(MetricDefinition(
    key="planning_score", name="Planning Score",
    description="Quality of multi-step reasoning and planning",
    score_range=(0.0, 1.0), default_weight=1.0, higher_is_better=True,
    applicable_judges=["llm", "trace"],
    calculation_method="llm_eval or step_match_ratio",
    requires_expected=False, requires_trace=True))

MetricRegistry.register(MetricDefinition(
    key="latency", name="Latency",
    description="Response latency score (higher = faster)",
    score_range=(0.0, 1.0), default_weight=0.5, higher_is_better=True,
    applicable_judges=["trace"],
    calculation_method="1.0 - (actual/max) with tiered scoring",
    requires_expected=False, requires_trace=True))

MetricRegistry.register(MetricDefinition(
    key="cost", name="Cost",
    description="Cost efficiency score (higher = cheaper)",
    score_range=(0.0, 1.0), default_weight=0.3, higher_is_better=True,
    applicable_judges=["trace"],
    calculation_method="1.0 - (actual/max) with tiered scoring",
    requires_expected=False, requires_trace=False))

MetricRegistry.register(MetricDefinition(
    key="coherence", name="Coherence",
    description="Response coherence and readability",
    score_range=(0.0, 1.0), default_weight=0.5, higher_is_better=True,
    applicable_judges=["llm"],
    calculation_method="llm_eval",
    requires_expected=False, requires_trace=False))

MetricRegistry.register(MetricDefinition(
    key="intent_match", name="Intent Match",
    description="Whether response matches expected intent",
    score_range=(0.0, 1.0), default_weight=1.0, higher_is_better=True,
    applicable_judges=["rule", "llm"],
    calculation_method="keyword_detection or llm_eval",
    requires_expected=True, requires_trace=False))

MetricRegistry.register(MetricDefinition(
    key="semantic_similarity", name="Semantic Similarity",
    description="Cosine similarity between response and reference",
    score_range=(0.0, 1.0), default_weight=1.0, higher_is_better=True,
    applicable_judges=["embedding"],
    calculation_method="cosine_similarity(embed(response), embed(reference))",
    requires_expected=True, requires_trace=False))

MetricRegistry.register(MetricDefinition(
    key="forbidden_check", name="Forbidden Check",
    description="Absence of forbidden content/patterns/tools",
    score_range=(0.0, 1.0), default_weight=0.5, higher_is_better=True,
    applicable_judges=["rule"],
    calculation_method="binary: 1.0 if no violation, 0.0 if any",
    requires_expected=True, requires_trace=False))

MetricRegistry.register(MetricDefinition(
    key="semantic_pass", name="Semantic Pass",
    description="Whether semantic similarity exceeds threshold",
    score_range=(0.0, 1.0), default_weight=0.5, higher_is_better=True,
    applicable_judges=["embedding"],
    calculation_method="binary: 1.0 if similarity >= threshold",
    requires_expected=True, requires_trace=False))
```

## 6. Trace-derived 指标计算器

### 6.1 设计

部分指标可直接从 Trace 数据计算，无需 Judge 调用。

```python
# judges/trace_derived.py
class TraceDerivedCalculator:
    """从 Trace 直接计算的指标"""

    def calculate(self, agent_execution: AgentExecution,
                  trace: Trace | None, scenario: Scenario) -> list[MetricScore]:
        scores = []
        if not trace:
            return scores

        # Latency
        latency_ms = agent_execution.latency_ms or 0
        max_latency = scenario.constraints_data.get("max_latency_ms", 10000)
        latency_score = self._tiered_score(latency_ms, max_latency)
        scores.append(MetricScore(
            metric_key="latency", metric_name="Latency",
            score=latency_score, weight=0.5,
            detail={"actual_ms": latency_ms, "max_ms": max_latency}))

        # Cost
        cost = agent_execution.cost_usd or 0.0
        max_cost = scenario.constraints_data.get("max_cost_usd", 0.05)
        cost_score = self._tiered_score(cost, max_cost)
        scores.append(MetricScore(
            metric_key="cost", metric_name="Cost",
            score=cost_score, weight=0.3,
            detail={"actual_usd": cost, "max_usd": max_cost}))

        # Tool Accuracy (from trace)
        tool_spans = self._flatten_spans(trace.root_span, "tool_call")
        if tool_spans:
            successful = sum(1 for s in tool_spans if s.status == "ok")
            tool_score = successful / len(tool_spans)
            scores.append(MetricScore(
                metric_key="tool_accuracy", metric_name="Tool Accuracy",
                score=round(tool_score, 4), weight=1.5,
                detail={"total_calls": len(tool_spans), "successful": successful}))

        return scores

    def _tiered_score(self, actual: float, max_val: float) -> float:
        if actual <= max_val * 0.3:
            return 1.0
        elif actual <= max_val * 0.5:
            return 0.8
        elif actual <= max_val * 0.8:
            return 0.5
        elif actual <= max_val:
            return 0.2
        return 0.0

    def _flatten_spans(self, span: TraceSpan, span_type: str) -> list[TraceSpan]:
        result = []
        if span.span_type == span_type:
            result.append(span)
        for child in span.children:
            result.extend(self._flatten_spans(child, span_type))
        return result
```

## 7. 指标展示规范

### 7.1 报告中的指标展示

| 指标 | 展示格式 | 颜色编码 |
|------|----------|----------|
| Correctness | 0.85 / 1.00 | >=0.8 绿, >=0.5 橙, <0.5 红 |
| Hallucination | 0.92 / 1.00 | >=0.8 绿, >=0.5 橙, <0.5 红 |
| Tool Accuracy | 0.75 / 1.00 | >=0.8 绿, >=0.5 橙, <0.5 红 |
| Latency | 850ms (score: 0.80) | score>=0.8 绿, >=0.5 橙, <0.5 红 |
| Cost | $0.012 (score: 0.76) | score>=0.8 绿, >=0.5 橙, <0.5 红 |

### 7.2 指标直方图

```
correctness distribution:
0.0-0.1: ██ (2)
0.1-0.2: █ (1)
0.2-0.3:  (0)
0.3-0.4:  (0)
0.4-0.5: ███ (3)
0.5-0.6: █████ (5)
0.6-0.7: ████████ (8)
0.7-0.8: ████████████ (12)
0.8-0.9: ██████████████████ (18)
0.9-1.0: ████████████████████ (20)
```

## 8. 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|----------|
| AC-M-01 | Correctness Rule 计算公式正确 | 单元测试 |
| AC-M-02 | Hallucination 分数 1.0 表示无幻觉 | 单元测试 |
| AC-M-03 | Tool Accuracy Rule 匹配逻辑正确 | 单元测试 |
| AC-M-04 | Tool Accuracy Trace-derived 计算正确 | 单元测试 |
| AC-M-05 | Memory Accuracy 无 memory 时返回 1.0 | 单元测试 |
| AC-M-06 | Planning Score 无多步需求时返回 1.0 | 单元测试 |
| AC-M-07 | Latency 分段评分正确 | 单元测试 |
| AC-M-08 | Cost 分段评分正确 | 单元测试 |
| AC-M-09 | Forbidden Check 任一违规返回 0.0 | 单元测试 |
| AC-M-10 | Semantic Similarity cosine 计算正确 | 单元测试 |
| AC-M-11 | Semantic Pass 阈值判定正确 | 单元测试 |
| AC-M-12 | 场景级 overall_score 加权平均计算正确 | 单元测试 |
| AC-M-13 | overall_verdict 按 0.8/0.5 阈值判定 | 单元测试 |
| AC-M-14 | 评测级 metric_aggregates 包含 mean/std/p50/p95 | 单元测试 |
| AC-M-15 | MetricRegistry 注册后可通过 key 查询 | 单元测试 |
| AC-M-16 | MetricRegistry.by_judge_type 返回正确子集 | 单元测试 |
| AC-M-17 | 同 metric 多 Judge 取加权平均 | 单元测试 |
| AC-M-18 | pass_rate = count(>=0.8) / total 计算正确 | 单元测试 |
