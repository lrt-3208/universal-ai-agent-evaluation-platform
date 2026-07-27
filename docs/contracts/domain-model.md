# Domain Model — 核心领域模型

> **Depends on**: `../tech-spec.md`  
> **Referenced by**: `../phases/phase-1-foundation.md`, `../phases/phase-2-scenario.md`, `../phases/phase-3-runner.md`, `../phases/phase-4-judge.md`, `../phases/phase-5-report.md`, `../phases/phase-6-regression.md`, `runtime-event-contract.md`, `plugin-manifest-contract.md`, `error-model-contract.md`  
> **ADR**: `../decisions/0001-adapter-spi-minimal-interface.md`, `../decisions/0002-conversation-trace-jsonb-storage.md`, `../decisions/0008-error-model-contract.md`

## 1. 目标

定义 AgentEval 系统的全部核心领域实体，包含字段级定义、关系约束与状态机。本文件是所有 Phase 实现的数据契约。

### Source of Truth 原则

> **Domain Model 是领域真相（Source of Truth）**。
>
> DTO、ORM Model、VO、DSL、API Contract、Event Payload 中的同名字段不得与 Domain Model 冲突。如需差异（如 DTO 隐藏字段、API 重命名字段），必须在映射层显式声明，且差异方向只能是从 Domain Model 向外投影，不允许反向覆盖。
>
> **执行规则**：
> 1. 新增字段时，先在 Domain Model 定义，再在各投影层（DTO/ORM/API）添加映射。
> 2. Code Review 必须检查 DTO/ORM 字段是否与 Domain Model 一致。
> 3. 如遇不可调和的冲突（如外部 API 强制字段名），通过 ADR 记录并声明映射规则。

## 2. 模型总览与关系

```
Workspace 1──* Project 1──* Dataset 1──* Scenario
                                    │
                    ┌───────────────┘
                    │
                Evaluation 1──* ScenarioExecution
                    │                    │
                    │                    │ 1
                    │                    │
                    │              AgentExecution 1──1 Trace
                    │                    │
                    │                    │ 1
                    │                    │
                    │              JudgeResult 1──* MetricScore
                    │
              Regression 1──* EvaluationPair
```

## 3. 枚举定义

```python
# domain/enums.py
from enum import Enum

class AgentAdapterType(str, Enum):
    HTTP = "http"
    OPENAI = "openai"
    CUSTOM = "custom"

class ScenarioStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"

class EvaluationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SCORING = "scoring"       # 执行完成，评分中
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ScenarioExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"

class JudgeType(str, Enum):
    RULE = "rule"
    LLM = "llm"
    EMBEDDING = "embedding"

class JudgeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TraceSpanType(str, Enum):
    ROOT = "root"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    RETRIEVAL = "retrieval"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    REASONING = "reasoning"

class ReportFormat(str, Enum):
    JSON = "json"
    HTML = "html"

class RegressionStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"

class RegressionVerdict(str, Enum):
    IMPROVED = "improved"
    REGRESSED = "regressed"
    UNCHANGED = "unchanged"
    FLAKY = "flaky"
```

## 4. Workspace

### 4.1 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 全局唯一 |
| name | str | 非空, 1-64字符 | 工作空间名称 |
| slug | str | 唯一, ^[a-z0-9-]+$ | URL 友好标识 |
| description | str | 可空, max 512 | 描述 |
| owner_id | str | 非空 | 创建者 ID |
| settings | dict | 默认 {} | 工作空间级配置覆盖 |
| created_at | datetime | 非空 | 创建时间 |
| updated_at | datetime | 非空 | 更新时间 |
| deleted_at | datetime | 可空 | 软删除时间 |

### 4.2 不变量

- `slug` 全局唯一，创建后不可修改。
- 删除 Workspace 时级联软删除其下所有 Project。

## 5. Project

### 5.1 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| workspace_id | UUID | FK → Workspace.id, 非空 | 所属工作空间 |
| name | str | 非空, 1-64字符 | 项目名称 |
| slug | str | 同 workspace 内唯一 | URL 标识 |
| description | str | 可空, max 512 | |
| agent_config | dict | 非空 | 默认 Agent 适配器配置 |
| default_judge_config | dict | 可空 | 默认评分配置 |
| tags | list[str] | 默认 [] | 标签 |
| created_at | datetime | 非空 | |
| updated_at | datetime | 非空 | |
| deleted_at | datetime | 可空 | |

### 5.2 agent_config 结构

```json
{
  "adapter_type": "openai",
  "endpoint": "https://api.openai.com/v1",
  "model": "gpt-4o",
  "api_key_ref": "vault://openai-key",  // 引用密钥，不存明文
  "temperature": 0.7,
  "max_tokens": 4096,
  "system_prompt": "You are a helpful assistant.",
  "headers": {}
}
```

## 6. Dataset

### 6.1 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| project_id | UUID | FK → Project.id, 非空 | 所属项目 |
| name | str | 非空, 1-128字符 | 数据集名称 |
| version | str | 非空, 语义化版本 (e.g. "1.0.0") | 版本号 |
| description | str | 可空, max 512 | |
| format | str | 非空, enum: "yaml" \| "json" \| "csv" | 源文件格式 |
| source_uri | str | 可空 | 源文件存储路径 (s3://...) |
| scenario_count | int | 默认 0 | 包含的 Scenario 数量 |
| tags | list[str] | 默认 [] | |
| metadata | dict | 默认 {} | 扩展元数据 |
| is_latest | bool | 默认 true | 是否为最新版本 |
| created_at | datetime | 非空 | |
| updated_at | datetime | 非空 | |
| deleted_at | datetime | 可空 | |

### 6.2 不变量

- `(project_id, name, version)` 三元组唯一。
- 导入新版本时，同 name 的旧版本 `is_latest` 置为 `false`。

## 7. Scenario

### 7.1 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| dataset_id | UUID | FK → Dataset.id, 非空 | 所属数据集 |
| external_id | str | 同 dataset 内唯一 | 数据集内部编号 (e.g. "S001") |
| title | str | 非空, 1-256字符 | 场景标题 |
| description | str | 可空 | 场景描述 |
| input | dict | 非空 | 用户输入（见 7.2） |
| history | list[dict] | 默认 [] | 对话历史（见 7.3） |
| memory | dict | 默认 {} | 预置记忆（见 7.4） |
| expected | dict | 默认 {} | 期望输出（见 7.5） |
| constraints | dict | 默认 {} | 约束条件（见 7.6） |
| judge_config | dict | 可空 | 场景级评分覆盖 |
| tags | list[str] | 默认 [] | |
| priority | int | 默认 0 | 执行优先级（越大越先） |
| metadata | dict | 默认 {} | |
| status | ScenarioStatus | 默认 DRAFT | |
| created_at | datetime | 非空 | |
| updated_at | datetime | 非空 | |
| deleted_at | datetime | 可空 | |

### 7.2 input 结构

```json
{
  "user_message": "帮我查一下北京明天的天气",
  "context": {
    "location": "北京",
    "date": "2026-07-05"
  },
  "attachments": [
    {
      "type": "image",
      "uri": "s3://bucket/img.png"
    }
  ]
}
```

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| user_message | str | 非空 | 用户输入消息 |
| context | dict | 可空 | 附加上下文 |
| attachments | list[dict] | 默认 [] | 附件列表 |

### 7.3 history 结构

```json
[
  {
    "role": "user",
    "content": "你好",
    "timestamp": "2026-07-04T10:00:00Z"
  },
  {
    "role": "assistant",
    "content": "你好！有什么可以帮你的？",
    "timestamp": "2026-07-04T10:00:01Z"
  }
]
```

### 7.4 memory 结构

```json
{
  "long_term": [
    {"key": "user_name", "value": "张三"}
  ],
  "working": {
    "current_task": "weather_query"
  },
  "max_tokens": 2048
}
```

### 7.5 expected 结构

```json
{
  "response_contains": ["北京", "天气"],
  "response_not_contains": ["不知道", "无法"],
  "tool_calls_expected": [
    {
      "tool_name": "get_weather",
      "args_match": {"location": "北京"}
    }
  ],
  "intent": "weather_query",
  "reference_answer": "北京明天晴天，气温25-35度。"
}
```

### 7.6 constraints 结构

```json
{
  "max_turns": 5,
  "max_latency_ms": 10000,
  "max_cost_usd": 0.05,
  "must_use_tools": ["get_weather"],
  "must_not_use_tools": ["send_email"],
  "language": "zh-CN",
  "forbidden_patterns": ["rm -rf", "DROP TABLE"]
}
```

## 8. Conversation

### 8.1 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| scenario_execution_id | UUID | FK → ScenarioExecution.id, 非空 | 关联执行 |
| messages | list[Message] | 非空 | 完整对话消息列表 |
| turn_count | int | 非空 | 对话轮数 |
| total_tokens | dict | 默认 {} | Token 统计 |

### 8.2 Message 结构

```python
class Message(BaseModel):
    role: str            # "user" | "assistant" | "system" | "tool"
    content: str         # 消息文本
    tool_calls: list[ToolCall] | None = None  # assistant 发起的工具调用
    tool_call_id: str | None = None           # tool 消息对应的调用 ID
    name: str | None = None                   # tool 名称
    timestamp: datetime
    metadata: dict = {}                       # token 数、模型名等
```

### 8.3 ToolCall 结构

```python
class ToolCall(BaseModel):
    id: str               # 调用 ID
    tool_name: str        # 工具名称
    arguments: dict       # 调用参数
    result: dict | None = None  # 执行结果
    latency_ms: int = 0         # 调用耗时
    status: str = "success"     # "success" | "error" | "timeout"
```

## 9. AgentExecution

### 9.1 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| scenario_execution_id | UUID | FK → ScenarioExecution.id, 非空 | 父执行 |
| agent_adapter_type | AgentAdapterType | 非空 | 适配器类型 |
| agent_config | dict | 非空 | 实际使用的 Agent 配置快照 |
| agent_version | str | 可空 | Agent 版本标识 |
| status | ScenarioExecutionStatus | 非空 | 执行状态 |
| conversation | Conversation | 可空 | 产生的对话 |
| trace_id | UUID | 可空 | 关联 Trace 根 ID |
| started_at | datetime | 非空 | 执行开始时间 |
| completed_at | datetime | 可空 | 执行完成时间 |
| latency_ms | int | 可空 | 总耗时 |
| error_message | str | 可空 | 失败原因 |
| retry_count | int | 默认 0 | 重试次数 |
| cost_usd | float | 可空 | 本次执行花费 |

## 10. Trace

### 10.1 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | Trace 根 ID |
| agent_execution_id | UUID | FK → AgentExecution.id, 非空 | 关联执行 |
| root_span | TraceSpan | 非空 | 根 Span |
| span_count | int | 非空 | Span 总数 |
| total_llm_calls | int | 非空 | LLM 调用次数 |
| total_tool_calls | int | 非空 | 工具调用次数 |
| total_tokens | dict | 非空 | Token 汇总 |
| started_at | datetime | 非空 | |
| completed_at | datetime | 可空 | |

### 10.2 TraceSpan 结构

```python
class TraceSpan(BaseModel):
    id: str                        # Span ID (UUID hex)
    trace_id: UUID                 # 所属 Trace
    parent_id: str | None          # 父 Span ID，根为 None
    span_type: TraceSpanType       # Span 类型
    name: str                      # 可读名称
    input_data: dict               # 输入数据
    output_data: dict              # 输出数据
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int
    status: str                    # "ok" | "error" | "timeout"
    attributes: dict = {}          # 额外属性
    children: list["TraceSpan"] = []  # 子 Span（嵌套树）
```

### 10.3 Span 类型输入输出

| Span 类型 | input_data | output_data |
|-----------|------------|-------------|
| llm_call | `{"messages": [...], "model": "...", "params": {...}}` | `{"response": "...", "tokens": {"prompt": N, "completion": M}, "finish_reason": "stop"}` |
| tool_call | `{"tool_name": "...", "arguments": {...}}` | `{"result": {...}, "status": "success"}` |
| retrieval | `{"query": "...", "top_k": N}` | `{"documents": [...]}` |
| memory_read | `{"keys": [...]}` | `{"entries": [...]}` |
| memory_write | `{"entries": [...]}` | `{"written_count": N}` |
| reasoning | `{"input": "...", "chain": [...]}` | `{"conclusion": "..."}` |

## 11. JudgeResult

### 11.1 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| agent_execution_id | UUID | FK → AgentExecution.id, 非空 | 被评分的执行 |
| judge_type | JudgeType | 非空 | 评分器类型 |
| judge_config | dict | 非空 | 评分配置快照 |
| status | JudgeStatus | 非空 | 评分状态 |
| metric_scores | list[MetricScore] | 非空 | 各指标得分 |
| overall_score | float | 可空 | 加权总分 [0.0, 1.0] |
| overall_verdict | str | 可空 | "pass" \| "fail" \| "partial" |
| reasoning | str | 可空 | 评分推理过程（LLM Judge） |
| started_at | datetime | 非空 | |
| completed_at | datetime | 可空 | |
| error_message | str | 可空 | |

### 11.2 MetricScore 结构

```python
class MetricScore(BaseModel):
    metric_key: str        # 指标键 (e.g. "correctness")
    metric_name: str       # 指标显示名
    score: float           # 得分 [0.0, 1.0]
    max_score: float = 1.0
    weight: float = 1.0    # 在 overall_score 中的权重
    detail: dict = {}      # 评分细节
    reasoning: str | None = None  # 该指标评分理由
```

## 12. Metrics

### 12.1 字段定义

Metrics 不是独立实体，而是 MetricScore 的汇总视图。Evaluation 级别的 Metrics 聚合结构如下：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| evaluation_id | UUID | 非空 | 所属评测 |
| scenario_count | int | 非空 | 场景总数 |
| executed_count | int | 非空 | 已执行数 |
| scored_count | int | 非空 | 已评分数 |
| metric_aggregates | dict | 非空 | 各指标聚合统计 |
| cost_total_usd | float | 非空 | 总花费 |
| latency_avg_ms | float | 非空 | 平均延迟 |
| latency_p50_ms | float | 非空 | P50 延迟 |
| latency_p95_ms | float | 非空 | P95 延迟 |
| latency_p99_ms | float | 非空 | P99 延迟 |
| pass_rate | float | 非空 | 通过率 [0.0, 1.0] |

### 12.2 metric_aggregates 结构

```json
{
  "correctness": {
    "mean": 0.85,
    "std": 0.12,
    "min": 0.40,
    "max": 1.00,
    "p50": 0.90,
    "p95": 0.98,
    "histogram": [0, 2, 5, 10, 20, 15, 8]
  },
  "hallucination": {
    "mean": 0.10,
    "std": 0.08,
    "min": 0.00,
    "max": 0.60,
    "p50": 0.05,
    "p95": 0.30,
    "histogram": [30, 15, 8, 4, 2, 1, 0]
  }
}
```

## 13. Report

### 13.1 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| evaluation_id | UUID | FK → Evaluation.id, 非空 | 关联评测 |
| format | ReportFormat | 非空 | 报告格式 |
| status | str | 非空 | "generating" \| "ready" \| "failed" |
| content_uri | str | 可空 | 报告文件存储路径 |
| summary | dict | 可空 | 报告摘要 |
| metrics_snapshot | dict | 可空 | 生成时的指标快照 |
| created_at | datetime | 非空 | |
| completed_at | datetime | 可空 | |

### 13.2 summary 结构

```json
{
  "total_scenarios": 100,
  "pass_rate": 0.85,
  "overall_score": 0.82,
  "failed_scenarios": 15,
  "top_failed_metrics": [
    {"metric": "tool_accuracy", "fail_count": 12},
    {"metric": "hallucination", "fail_count": 8}
  ],
  "cost_total_usd": 3.52,
  "duration_seconds": 240
}
```

## 14. Regression

### 14.1 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| project_id | UUID | FK → Project.id, 非空 | 所属项目 |
| name | str | 非空, 1-128字符 | 回归分析名称 |
| baseline_evaluation_id | UUID | 非空 | 基线评测 ID |
| target_evaluation_id | UUID | 非空 | 目标评测 ID |
| status | RegressionStatus | 非空 | 分析状态 |
| scenario_diffs | list[ScenarioDiff] | 可空 | 逐场景差异 |
| metric_diffs | dict | 可空 | 指标级差异 |
| overall_verdict | RegressionVerdict | 可空 | 总体结论 |
| summary | dict | 可空 | 摘要 |
| created_at | datetime | 非空 | |
| completed_at | datetime | 可空 | |

### 14.2 ScenarioDiff 结构

```python
class ScenarioDiff(BaseModel):
    scenario_id: UUID
    external_id: str
    baseline_score: float | None
    target_score: float | None
    score_delta: float | None       # target - baseline
    baseline_verdict: str | None
    target_verdict: str | None
    verdict: RegressionVerdict       # improved | regressed | unchanged | flaky
    metric_deltas: dict[str, float] # {"correctness": -0.1, "tool_accuracy": 0.05}
    notes: str | None = None
```

### 14.3 metric_diffs 结构

```json
{
  "correctness": {
    "baseline_mean": 0.82,
    "target_mean": 0.88,
    "delta": 0.06,
    "direction": "improved"
  },
  "tool_accuracy": {
    "baseline_mean": 0.75,
    "target_mean": 0.70,
    "delta": -0.05,
    "direction": "regressed"
  }
}
```

### 14.4 summary 结构

```json
{
  "total_compared": 100,
  "improved": 25,
  "regressed": 10,
  "unchanged": 60,
  "flaky": 5,
  "baseline_pass_rate": 0.82,
  "target_pass_rate": 0.88,
  "pass_rate_delta": 0.06,
  "regression_risk": "low"
}
```

## 15. Evaluation（补充实体）

### 15.1 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| project_id | UUID | FK → Project.id, 非空 | 所属项目 |
| name | str | 非空, 1-128字符 | 评测名称 |
| dataset_id | UUID | FK → Dataset.id, 非空 | 评测数据集 |
| agent_config | dict | 非空 | Agent 配置快照 |
| judge_configs | list[dict] | 非空 | 评分器配置列表 |
| status | EvaluationStatus | 默认 PENDING | 评测状态 |
| scenario_executions | list[ScenarioExecution] | 默认 [] | 场景执行列表 |
| config | dict | 默认 {} | 执行配置（并发数、超时等） |
| version_label | str | 可空 | 版本标签 (e.g. "v2.1-baseline") |
| started_at | datetime | 可空 | |
| completed_at | datetime | 可空 | |
| error_message | str | 可空 | |
| created_by | str | 非空 | 创建者 |
| created_at | datetime | 非空 | |
| updated_at | datetime | 非空 | |

### 15.2 config 结构

```json
{
  "max_concurrent": 10,
  "timeout_seconds": 120,
  "retry_count": 2,
  "retry_delay_seconds": 5,
  "collect_trace": true,
  "auto_judge": true,
  "filter_tags": ["critical"],
  "filter_priority_min": 0
}
```

## 16. ScenarioExecution（补充实体）

### 16.1 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| evaluation_id | UUID | FK → Evaluation.id, 非空 | 所属评测 |
| scenario_id | UUID | FK → Scenario.id, 非空 | 被测场景 |
| status | ScenarioExecutionStatus | 默认 PENDING | |
| agent_execution | AgentExecution | 可空 | Agent 执行结果 |
| judge_results | list[JudgeResult] | 默认 [] | 评分结果列表 |
| overall_score | float | 可空 | 综合得分 |
| overall_verdict | str | 可空 | |
| started_at | datetime | 可空 | |
| completed_at | datetime | 可空 | |
| error_message | str | 可空 | |
| retry_count | int | 默认 0 | |

## 17. 状态机定义

### 17.1 Evaluation 状态机

```
PENDING ──(start)──> RUNNING ──(all_scenarios_done)──> SCORING ──(all_judges_done)──> COMPLETED
   │                     │                                   │
   │                     ├──(error)──> FAILED                └──(error)──> FAILED
   │                     │
   └──(cancel)──> CANCELLED
                   RUNNING ──(cancel)──> CANCELLED
```

### 17.2 ScenarioExecution 状态机

```
PENDING ──(dispatch)──> RUNNING ──(success)──> COMPLETED
                          ├──(error)──> FAILED
                          ├──(timeout)──> TIMEOUT
                          └──(skip)──> SKIPPED
```

### 17.3 JudgeResult 状态机

```
PENDING ──(start)──> RUNNING ──(done)──> COMPLETED
                       └──(error)──> FAILED
```

### 17.4 Regression 状态机

```
PENDING ──(start)──> ANALYZING ──(done)──> COMPLETED
                       └──(error)──> FAILED
```

## 18. DB 级约束补充

> 以下约束是对前述各实体字段定义的补充，作为 Alembic 迁移和 ORM 模型定义的最终依据。

### 18.1 CHECK 约束

| 表 | 字段 | 约束表达式 | 说明 |
|------|------|------------|------|
| metric_scores | score | `score >= 0.0 AND score <= max_score` | 得分范围 |
| metric_scores | weight | `weight >= 0.0` | 权重非负 |
| judge_results | overall_score | `overall_score IS NULL OR (overall_score >= 0.0 AND overall_score <= 1.0)` | 总分范围 |
| evaluations | status | `status IN ('pending','running','scoring','completed','failed','cancelled')` | 状态枚举 |
| scenario_executions | status | `status IN ('pending','running','completed','failed','timeout','skipped')` | 状态枚举 |
| scenarios | priority | `priority >= 0 AND priority <= 100` | 优先级范围 |
| datasets | version | `version ~ '^\d+\.\d+\.\d+$'` | 语义化版本格式 |
| agent_executions | retry_count | `retry_count >= 0` | 重试次数非负 |
| evaluations | config | `config ? 'max_concurrent' AND (config->>'max_concurrent')::int BETWEEN 1 AND 100` | 并发范围 |
| regressions | scenario_diffs | `scenario_diffs IS NULL OR jsonb_typeof(scenario_diffs) = 'array'` | JSONB 类型检查 |

### 18.2 UNIQUE 约束

| 表 | 约束名 | 字段组合 | 说明 |
|------|---------|----------|------|
| workspaces | uq_workspaces_slug | slug | 全局唯一 |
| projects | uq_projects_workspace_slug | (workspace_id, slug) | 工作空间内唯一 |
| datasets | uq_datasets_project_name_version | (project_id, name, version) | 三元组唯一 |
| scenarios | uq_scenarios_dataset_external_id | (dataset_id, external_id) | 数据集内唯一 |
| reports | uq_reports_eval_format | (evaluation_id, format) | 同评测同格式唯一 |

### 18.3 INDEX 规范

| 表 | 索引名 | 字段 | 类型 | 说明 |
|------|--------|------|------|------|
| workspaces | ix_workspaces_slug | slug | btree | 唯一查找 |
| workspaces | ix_workspaces_owner | owner_id | btree | 按创建者查询 |
| projects | ix_projects_workspace | (workspace_id, deleted_at) | btree | 级联查询 |
| datasets | ix_datasets_project | (project_id, is_latest, deleted_at) | btree | 最新版本查询 |
| scenarios | ix_scenarios_dataset_tags | dataset_id, tags | GIN | tags JSONB 包含查询 |
| scenarios | ix_scenarios_dataset_priority | (dataset_id, priority DESC) WHERE deleted_at IS NULL | btree partial | 优先级排序 |
| evaluations | ix_evaluations_project_status | (project_id, status) | btree | 按状态筛选 |
| scenario_executions | ix_scnexec_evaluation | (evaluation_id, status) | btree | 按评测查询执行 |
| agent_executions | ix_agentexec_scnexec | scenario_execution_id | btree | 关联查询 |
| judge_results | ix_judge_agentexec | (agent_execution_id, judge_type) | btree | 按执行查询评分 |
| traces | ix_traces_agentexec | agent_execution_id | btree | 按执行查询 Trace |
| reports | ix_reports_evaluation | (evaluation_id, format) | btree | 按评测查询报告 |
| regressions | ix_regressions_project | (project_id, status) | btree | 按项目查询回归 |

### 18.4 JSONB Schema 校验规则

> MVP 阶段使用 Pydantic 模型在应用层校验；PostgreSQL 16 可选启用 `CHECK (jsonb_matches_schema(...))`。

| 字段 | 所属实体 | 必须包含的 Key | Key 类型约束 |
|------|----------|----------------|-------------|
| agent_config | Project / Evaluation | adapter_type, model | adapter_type: enum; model: str非空 |
| config | Evaluation | max_concurrent, timeout_seconds | 均为 int，范围见 CHECK |
| input | Scenario | user_message | str 非空 |
| expected | Scenario | (至少一个) | response_contains \| reference_answer \| tool_calls_expected \| intent |
| constraints | Scenario | (可全空) | max_turns: int>0; max_latency_ms: int>0 |
| judge_config | JudgeResult | judge_type, enabled | judge_type: enum; enabled: bool |
| config | JudgeConfig | judge_type | enum |
| summary | Report | total_scenarios, pass_rate | int; float [0,1] |
| scenario_diffs | Regression | (array) | 每个元素含 scenario_id, verdict |

### 18.5 字段级验证规则

| 实体 | 字段 | 规则 | 错误码 |
|------|------|------|--------|
| Workspace | slug | `^[a-z0-9-]+$, 1-64字符, 创建后不可变` | 40001 |
| Project | slug | `^[a-z0-9-]+$, 1-64字符, 同 workspace 内唯一` | 40002 |
| Dataset | version | `^\d+\.\d+\.\d+$, 语义化版本` | 40003 |
| Dataset | format | `enum: yaml | json | csv` | 40004 |
| Scenario | external_id | `^[A-Za-z0-9_-]+$, 1-64字符, 同 dataset 内唯一` | 40005 |
| Scenario | priority | `0-100, 默认 0` | 40006 |
| Evaluation | config.max_concurrent | `1-100, 默认 10` | 40007 |
| Evaluation | config.timeout_seconds | `1-3600, 默认 120` | 40008 |
| MetricScore | score | `0.0 <= score <= max_score (默认 1.0)` | 40009 |
| MetricScore | weight | `>= 0.0, 默认 1.0` | 40010 |
| JudgeResult | overall_score | `NULL 或 0.0-1.0` | 40011 |
| Report | format | `enum: json | html` | 40012 |
| Message | role | `enum: user | assistant | system | tool` | 40013 |
| ToolCall | status | `enum: success | error | timeout` | 40014 |
| TraceSpan | status | `enum: ok | error | timeout` | 40015 |

## 19. 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|----------|
| AC-01-01 | 所有实体的 UUID 字段为 v4 格式 | 单元测试 |
| AC-01-02 | Scenario.expected 必须包含至少一个评分依据字段 | DSL 校验测试 |
| AC-01-03 | Evaluation 状态只能按状态机定义的路径流转 | 单元测试 |
| AC-01-04 | Dataset 同 name 新版本导入后旧版本 is_latest=false | 集成测试 |
| AC-01-05 | TraceSpan 的 children 形成有效的树结构（无环） | 单元测试 |
| AC-01-06 | MetricScore.score 范围为 [0.0, max_score] | 单元测试 |
| AC-01-07 | ScenarioDiff.verdict 值在枚举范围内 | 单元测试 |
| AC-01-08 | 软删除的 Dataset 下 Scenario 不可被引用到新 Evaluation | 集成测试 |
