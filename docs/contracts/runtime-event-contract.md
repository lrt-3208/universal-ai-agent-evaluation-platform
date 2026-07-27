# Runtime Event Contract — 运行时事件契约

> **Depends on**: `domain-model.md`  
> **Referenced by**: `../phases/phase-3-runner.md`, `../phases/phase-4-judge.md`, `../phases/phase-5-report.md`, `../phases/phase-6-regression.md`  
> **ADR**: `../decisions/0007-runtime-event-and-plugin-manifest-contracts.md`

## 1. 定位

定义 AgentEval 运行时事件的 **Schema**、**Delivery Semantics** 和 **Transport Bindings**。本契约与传输协议解耦——Event Schema 是 MUST（冻结），Delivery Semantics 是 MUST（冻结），Transport Bindings 是 MAY（可扩展）。

## 2. 三层架构

```
Runtime Event Contract
│
├── Layer 1: Event Schema (MUST — 冻结)
│   └── EventEnvelope + Core Event Types
│
├── Layer 2: Delivery Semantics (MUST — 冻结)
│   └── 顺序保证 + 幂等性 + 持久化
│
└── Layer 3: Transport Bindings (MAY — 可扩展)
    ├── WebSocket (MVP 实现)
    ├── SSE (未来)
    ├── Webhook (未来)
    └── Message Queue (未来)
```

**原则**：Contract 定义 Event，不定义 Transport。新增 Transport Binding 不修改 Event Schema。

---

## Layer 1: Event Schema (MUST)

### 3. 统一事件信封

```python
# schemas/events.py
from datetime import datetime
from uuid import UUID
from typing import Literal

class EventEnvelope(BaseModel):
    """MUST: 所有运行时事件的统一信封"""
    event_id: UUID                    # 事件唯一 ID (v4)
    event_type: str                   # 事件类型 (e.g. "evaluation.started")
    domain: str                       # 事件域 (evaluation | scenario | judge | report | regression | plugin | system)
    timestamp: datetime               # 事件产生时间 (UTC, ISO 8601)
    workspace_id: UUID                # 工作空间 ID
    project_id: UUID | None           # 项目 ID (系统级事件可空)
    resource_id: UUID                 # 主体资源 ID
    parent_id: UUID | None            # 父资源 ID
    version: str = "1.0"              # 事件 Schema 版本
    payload: dict                     # 事件特定 Payload
    severity: Literal["info", "warn", "error"] = "info"
```

### 4. Core Event Types (MUST — 冻结)

> Core Event 是跨所有 Agent 框架（LangGraph / OpenAI Agents / Claude Code 等）通用的、语义稳定的事件。冻结后不新增、不修改，扩展事件通过 MAY 声明。

| event_type | domain | 触发时机 | severity | payload |
|------------|--------|----------|----------|---------|
| `evaluation.started` | evaluation | Runner 开始执行 | info | `{started_at, scenario_count, max_concurrent}` |
| `evaluation.completed` | evaluation | 所有评分完成 | info | `{completed_at, pass_rate, overall_score, cost_total_usd}` |
| `evaluation.failed` | evaluation | 执行失败 | error | `{failed_at, error_message}` |
| `scenario.completed` | scenario | 单个 Scenario 执行+评分完成 | info | `{scenario_id, external_id, latency_ms, overall_score, overall_verdict}` |
| `scenario.failed` | scenario | 单个 Scenario 执行失败 | error | `{scenario_id, external_id, error_message, will_retry}` |
| `judge.completed` | judge | 单个 Judge 评分完成 | info | `{agent_execution_id, judge_type, metric_count, duration_ms}` |
| `system.error` | system | 系统级错误 | error | `{error_type, error_message, context}` |
| `lifecycle.changed` | evaluation | 资源状态机流转 | info | `{resource_type, from_status, to_status, resource_id}` |

**Core Event payload 共享字段**：
所有 Core Event 的 payload **MUST** 包含 `resource_id`（与信封的 `resource_id` 一致），**SHOULD** 包含 `timestamp`（与信封一致）。

### 5. Extension Events (MAY — 可扩展)

> Extension Event 是特定场景的细化事件，可按需添加，不需修改本契约。每个 Extension Event 必须声明所属 domain 和触发条件。

| event_type | domain | 触发时机 | 状态 | 说明 |
|------------|--------|----------|------|------|
| `evaluation.created` | evaluation | Evaluation 创建 | MAY | 创建通知 |
| `evaluation.progress` | evaluation | 每完成一个 Scenario | MAY | 进度推送 |
| `evaluation.scoring` | evaluation | 进入评分阶段 | MAY | 阶段切换通知 |
| `evaluation.cancelled` | evaluation | 用户取消 | MAY | 取消通知 |
| `scenario.dispatched` | scenario | 分发到并发队列 | MAY | 调度追踪 |
| `scenario.started` | scenario | Adapter 开始执行 | MAY | 执行追踪 |
| `scenario.timeout` | scenario | 执行超时 | MAY | 超时追踪 |
| `scenario.retried` | scenario | 触发重试 | MAY | 重试追踪 |
| `scenario.skipped` | scenario | 跳过执行 | MAY | 跳过追踪 |
| `judge.started` | judge | JudgeService 开始评分 | MAY | 评分追踪 |
| `judge.judge_failed` | judge | 单个 Judge 失败 | MAY | 失败追踪 |
| `report.requested` | report | 用户请求报告 | MAY | 报告追踪 |
| `report.ready` | report | 报告生成完成 | MAY | 下载通知 |
| `report.failed` | report | 生成失败 | MAY | 失败追踪 |
| `regression.created` | regression | 回归分析创建 | MAY | 创建通知 |
| `regression.completed` | regression | 分析完成 | MAY | 完成通知 |
| `regression.failed` | regression | 分析失败 | MAY | 失败追踪 |
| `system.adapter_error` | system | Adapter 连接异常 | MAY | 告警 |
| `system.llm_quota_warning` | system | LLM 配额接近上限 | MAY | 告警 |
| `system.db_connection_lost` | system | 数据库连接中断 | MAY | 告警 |

**Extension Event 新增规则**：
- 新增 Extension Event 不需修改本契约，只需在对应 Phase 文档中声明
- Extension Event 必须使用已定义的 domain 前缀
- Extension Event 的 payload 结构在 Phase 文档中定义

---

## Layer 2: Delivery Semantics (MUST)

### 6. 顺序保证

| 范围 | 保证 | 实现方式 |
|------|------|----------|
| 同一 resource_id | **FIFO 有序** | 使用 Redis Stream (`XADD`) 缓冲，消费者按序读取 |
| 跨 resource_id | **不保证** | 消费者基于 `timestamp` 排序 |
| 断线重连 | **续传** | per-resource 序列号，重连后从上次序列号续传 |

### 7. 幂等性

- 消费者 **MUST** 基于 `event_id` 去重
- 断线重连后可能收到重复事件，消费者应幂等处理
- EventEnvelope 的 `event_id` 为 UUID v4，全局唯一

### 8. 事件持久化

```sql
CREATE TABLE event_log (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    event_type VARCHAR(128) NOT NULL,
    domain VARCHAR(32) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    workspace_id UUID NOT NULL,
    project_id UUID,
    resource_id UUID NOT NULL,
    parent_id UUID,
    payload JSONB NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'info',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_event_log_resource ON event_log (resource_id, timestamp);
CREATE INDEX ix_event_log_workspace ON event_log (workspace_id, timestamp);
CREATE INDEX ix_event_log_type ON event_log (event_type, timestamp);
```

### 9. 保留策略

| 事件域 | 保留时长 | 清理方式 |
|--------|----------|----------|
| Core Events (所有域) | 90 天 | 定时任务清理 |
| Extension Events (error) | 180 天 | 定时任务清理 |
| Extension Events (info/warn) | 30 天 | 定时任务清理 |

---

## Layer 3: Transport Bindings (MAY)

> 以下 Transport Bindings 均为可选实现。MVP 阶段实现 WebSocket，其余通过 ADR 演进。

### 10. WebSocket Binding (MVP)

#### 10.1 频道命名

```
ws://host/api/v1/ws/{channel}
```

| 频道 | 路径参数 | 订阅事件域 | 鉴权 |
|------|----------|-----------|------|
| Workspace | `/ws/workspaces/{workspace_id}` | system.* | Workspace 成员 |
| Project | `/ws/projects/{project_id}` | evaluation.*, regression.*, system.* | Project 成员 |
| Evaluation | `/ws/evaluations/{evaluation_id}` | evaluation.*, scenario.*, judge.*, report.* | Evaluation 创建者 |
| Regression | `/ws/regressions/{regression_id}` | regression.* | Regression 创建者 |

#### 10.2 订阅协议

```json
// 客户端 → 服务端
{"action": "subscribe", "channels": ["evaluation:eval-uuid"]}
{"action": "unsubscribe", "channels": ["evaluation:eval-uuid"]}

// 服务端 → 客户端
{"action": "subscribed", "channels": ["evaluation:eval-uuid"]}
{"action": "error", "message": "Evaluation not found", "code": 40404}
```

#### 10.3 心跳

```
客户端每 30s: {"action": "ping"}
服务端响应: {"action": "pong", "timestamp": "..."}
超时: 60s 无心跳断开
```

### 11. SSE Binding (未来)

> 通过 ADR 新增。复用 EventEnvelope，使用 `text/event-stream`，`data` 字段为 EventEnvelope JSON。

### 12. Webhook Binding (未来)

> 通过 ADR 新增。HTTP POST 投递 EventEnvelope，HMAC-SHA256 签名，重试 3 次。

### 13. Message Queue Binding (未来)

> 通过 ADR 新增。Kafka / RabbitMQ topic 映射，EventEnvelope 作为 message body。

---

## 14. MUST / SHOULD / MAY 汇总

| 层 | 规范级别 | 内容 |
|----|----------|------|
| Layer 1 | **MUST** | EventEnvelope 信封、8 个 Core Event Types、Extension Event 新增规则 |
| Layer 2 | **MUST** | FIFO 顺序保证、event_id 幂等去重、event_log 持久化表、保留策略 |
| Layer 3 | **MAY** | WebSocket Binding（MVP 实现）、SSE / Webhook / MQ（未来 ADR） |
| — | **SHOULD** | 断线重连续传、心跳超时 60s |

## 15. 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|----------|
| AC-EVT-01 | 所有 Core Event 在对应触发点正确发射 | 集成测试 |
| AC-EVT-02 | EventEnvelope 包含全部必填字段 | 消息体校验 |
| AC-EVT-03 | event_log 表记录所有已发出事件 | DB 查询 |
| AC-EVT-04 | 同 resource_id 事件按 FIFO 交付 | 顺序测试 |
| AC-EVT-05 | 重复 event_id 被消费者正确去重 | 幂等性测试 |
| AC-EVT-06 | WebSocket 频道订阅/取消订阅生效 | wscat 测试 |
| AC-EVT-07 | 断线重连后从上次序列号续传 | 断线重连测试 |
| AC-EVT-08 | 心跳 60s 超时后连接自动断开 | 超时测试 |
| AC-EVT-09 | Extension Event 不修改本契约即可新增 | 文档审查 |
# Runtime Event Contract — 运行时事件契约

> **Depends on**: `domain-model.md`  
> **Referenced by**: `../phases/phase-3-runner.md`, `../phases/phase-4-judge.md`, `../phases/phase-5-report.md`, `../phases/phase-6-regression.md`  
> **ADR**: 无

## 1. 定位

定义 AgentEval 运行时产生的事件类型、Payload 结构、交付机制与顺序保证。本契约是 WebSocket 实时推送、Celery 任务状态同步、Webhook 通知和审计日志的统一事件源。

## 2. 事件分类总览

| 事件域 | 前缀 | 触发 Phase | 交付方式 |
|--------|------|-----------|----------|
| Evaluation 生命周期 | `evaluation.*` | Phase 3 | WebSocket + Webhook (MAY) |
| Scenario 执行 | `scenario.*` | Phase 3 | WebSocket |
| Judge 评分 | `judge.*` | Phase 4 | WebSocket |
| Report 生成 | `report.*` | Phase 5 | WebSocket + 下载通知 |
| Regression 分析 | `regression.*` | Phase 6 | WebSocket + Webhook (MAY) |
| Plugin 生命周期 | `plugin.*` | Phase 7 | WebSocket (MAY) |
| 系统告警 | `system.*` | 全局 | WebSocket + 日志 |

## 3. 统一事件信封

所有事件共享统一信封结构：

```python
# schemas/events.py
from datetime import datetime
from uuid import UUID
from typing import Literal

class EventEnvelope(BaseModel):
    """MUST: 所有运行时事件的统一信封"""
    event_id: UUID                    # 事件唯一 ID (v4)
    event_type: str                   # 事件类型 (e.g. "evaluation.started")
    domain: str                       # 事件域 (evaluation | scenario | judge | report | regression | plugin | system)
    timestamp: datetime               # 事件产生时间 (UTC, ISO 8601)
    workspace_id: UUID                # 工作空间 ID
    project_id: UUID | None           # 项目 ID (系统级事件可空)
    resource_id: UUID                 # 主体资源 ID (Evaluation ID / ScenarioExecution ID 等)
    parent_id: UUID | None            # 父资源 ID (e.g. ScenarioExecution → Evaluation)
    version: str = "1.0"              # 事件 Schema 版本
    payload: dict                     # 事件特定 Payload (见 §4)
    severity: Literal["info", "warn", "error"] = "info"
```

### WebSocket 消息格式

```json
{
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_type": "evaluation.started",
    "domain": "evaluation",
    "timestamp": "2026-07-04T12:00:00.000Z",
    "workspace_id": "ws-uuid",
    "project_id": "proj-uuid",
    "resource_id": "eval-uuid",
    "parent_id": null,
    "version": "1.0",
    "payload": { /* ... */ },
    "severity": "info"
}
```

## 4. 事件类型定义

### 4.1 Evaluation 事件 (Phase 3)

| event_type | 触发时机 | severity | payload 结构 |
|------------|----------|----------|-------------|
| `evaluation.created` | Evaluation 创建 | info | `{name, dataset_id, scenario_count, agent_config_summary}` |
| `evaluation.started` | Runner 开始执行 | info | `{started_at, max_concurrent, scenario_count}` |
| `evaluation.progress` | 每完成一个 Scenario | info | `{completed, total, failed, running, pass_rate_current}` |
| `evaluation.scoring` | 所有 Scenario 执行完成，进入评分 | info | `{executed_count, failed_count, timeout_count}` |
| `evaluation.completed` | 所有评分完成 | info | `{completed_at, overall_pass_rate, overall_score, cost_total_usd}` |
| `evaluation.failed` | 执行失败 | error | `{failed_at, error_message, failed_scenario_count}` |
| `evaluation.cancelled` | 用户取消 | warn | `{cancelled_at, completed_count, skipped_count}` |

**evaluation.progress payload 示例**:
```json
{
    "completed": 45,
    "total": 100,
    "failed": 3,
    "running": 10,
    "pass_rate_current": 0.88,
    "avg_latency_ms": 3200,
    "estimated_remaining_seconds": 180
}
```

### 4.2 Scenario 执行事件 (Phase 3)

| event_type | 触发时机 | severity | payload 结构 |
|------------|----------|----------|-------------|
| `scenario.dispatched` | Runner 分发 Scenario 到并发队列 | info | `{scenario_id, external_id, attempt}` |
| `scenario.started` | Adapter 开始执行 | info | `{scenario_id, external_id, adapter_type, timeout_seconds}` |
| `scenario.completed` | Adapter 执行成功 | info | `{scenario_id, external_id, latency_ms, token_count, tool_call_count}` |
| `scenario.failed` | Adapter 执行失败 | error | `{scenario_id, external_id, error_message, retry_count, will_retry}` |
| `scenario.timeout` | 执行超时 | error | `{scenario_id, external_id, timeout_seconds, partial_response}` |
| `scenario.retried` | 触发重试 | warn | `{scenario_id, external_id, attempt, max_retries, delay_seconds}` |
| `scenario.skipped` | 跳过执行 | warn | `{scenario_id, external_id, reason}` |

### 4.3 Judge 事件 (Phase 4)

| event_type | 触发时机 | severity | payload 结构 |
|------------|----------|----------|-------------|
| `judge.started` | JudgeService 开始评分 | info | `{agent_execution_id, judge_types: ["rule","llm"], scenario_id}` |
| `judge.judge_completed` | 单个 Judge 完成 | info | `{judge_type, metric_count, duration_ms}` |
| `judge.judge_failed` | 单个 Judge 失败 | error | `{judge_type, error_message}` |
| `judge.completed` | 所有 Judge 完成 | info | `{overall_score, overall_verdict, metric_count, total_duration_ms}` |

### 4.4 Report 事件 (Phase 5)

| event_type | 触发时机 | severity | payload 结构 |
|------------|----------|----------|-------------|
| `report.requested` | 用户请求生成报告 | info | `{evaluation_id, format, include_trace}` |
| `report.generating` | 开始生成 | info | `{format, estimated_seconds}` |
| `report.ready` | 报告生成完成 | info | `{format, content_uri, file_size_bytes, summary_preview}` |
| `report.failed` | 生成失败 | error | `{format, error_message}` |

### 4.5 Regression 事件 (Phase 6)

| event_type | 触发时机 | severity | payload 结构 |
|------------|----------|----------|-------------|
| `regression.created` | 回归分析创建 | info | `{baseline_evaluation_id, target_evaluation_id, name}` |
| `regression.analyzing` | 开始分析 | info | `{matched_scenario_count}` |
| `regression.completed` | 分析完成 | info | `{improved, regressed, unchanged, flaky, regression_risk}` |
| `regression.failed` | 分析失败 | error | `{error_message}` |

### 4.6 系统事件 (全局)

| event_type | 触发时机 | severity | payload 结构 |
|------------|----------|----------|-------------|
| `system.adapter_error` | Adapter 连接异常 | error | `{adapter_type, endpoint, error_type, error_message}` |
| `system.llm_quota_warning` | LLM 配额接近上限 | warn | `{provider, remaining_quota, threshold}` |
| `system.db_connection_lost` | 数据库连接中断 | error | `{retry_attempt, will_retry}` |
| `system.celery_worker_offline` | Celery Worker 离线 | error | `{worker_name, active_task_count}` |

## 5. WebSocket 频道设计

### 5.1 频道命名

```
ws://host/api/v1/ws/{channel}
```

| 频道 | 路径参数 | 订阅事件域 | 鉴权 |
|------|----------|-----------|------|
| Workspace 频道 | `/ws/workspaces/{workspace_id}` | system.* | Workspace 成员 |
| Project 频道 | `/ws/projects/{project_id}` | evaluation.*, regression.*, system.* | Project 成员 |
| Evaluation 频道 | `/ws/evaluations/{evaluation_id}` | evaluation.*, scenario.*, judge.*, report.* | Evaluation 创建者 |
| Regression 频道 | `/ws/regressions/{regression_id}` | regression.* | Regression 创建者 |

### 5.2 订阅/取消订阅消息

```json
// 客户端 → 服务端
{"action": "subscribe", "channels": ["evaluation:eval-uuid", "regression:reg-uuid"]}
{"action": "unsubscribe", "channels": ["evaluation:eval-uuid"]}

// 服务端 → 客户端
{"action": "subscribed", "channels": ["evaluation:eval-uuid"]}
{"action": "unsubscribed", "channels": ["evaluation:eval-uuid"]}
{"action": "error", "message": "Evaluation not found", "code": 40404}
```

### 5.3 心跳机制

```
// 客户端每 30s 发送
{"action": "ping"}

// 服务端响应
{"action": "pong", "timestamp": "2026-07-04T12:00:30.000Z"}
```

超时策略：60s 无心跳则断开连接。

## 6. 事件顺序保证

### 6.1 同资源内顺序

同一 `resource_id` 的事件 **MUST** 按产生顺序交付：
- 使用 Redis Stream（`XADD`）作为事件缓冲，消费者按 `event_id` 顺序读取
- WebSocket 连接维护 per-resource 序列号，断线重连后从上次序列号续传

### 6.2 跨资源顺序

跨资源事件 **不保证** 全局顺序，消费者应基于 `timestamp` 排序。

### 6.3 幂等性

- 消费者 **MUST** 基于 `event_id` 去重
- 断线重连后可能收到重复事件，消费者应幂等处理

## 7. 事件持久化

### 7.1 事件日志表

```sql
CREATE TABLE event_log (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    event_type VARCHAR(128) NOT NULL,
    domain VARCHAR(32) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    workspace_id UUID NOT NULL,
    project_id UUID,
    resource_id UUID NOT NULL,
    parent_id UUID,
    payload JSONB NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'info',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_event_log_resource ON event_log (resource_id, timestamp);
CREATE INDEX ix_event_log_workspace ON event_log (workspace_id, timestamp);
CREATE INDEX ix_event_log_type ON event_log (event_type, timestamp);
```

### 7.2 保留策略

| 事件域 | 保留时长 | 清理方式 |
|--------|----------|----------|
| evaluation.* / scenario.* | 90 天 | 定时任务清理 |
| judge.* / report.* | 90 天 | 定时任务清理 |
| regression.* | 180 天 | 定时任务清理 |
| system.* (error) | 180 天 | 定时任务清理 |
| system.* (info/warn) | 30 天 | 定时任务清理 |

## 8. Webhook 扩展 (MAY)

> **状态**: 预留扩展点。MVP 通过 WebSocket 推送，Webhook 为可选扩展。

### 8.1 Webhook 注册

```json
POST /api/v1/webhooks
{
    "url": "https://your-server.com/webhook",
    "events": ["evaluation.completed", "regression.completed", "system.adapter_error"],
    "secret": "whsec_..."
}
```

### 8.2 Webhook 投递

- HTTP POST，Body 为 EventEnvelope JSON
- Header: `X-AgentEval-Signature: sha256={hmac}`
- 超时 10s，重试 3 次（指数退避）
- HTTP 2xx 视为成功，否则重试

## 9. MUST / SHOULD / MAY 规范

| 规范级别 | 要求 |
|----------|------|
| **MUST** | EventEnvelope 信封结构、事件类型命名规范、WebSocket 频道设计、事件幂等性、事件日志表 |
| **SHOULD** | evaluation.progress 事件的 estimated_remaining_seconds、WebSocket 心跳机制 |
| **MAY** | Webhook 投递、事件保留策略可配置、system.* 事件自定义扩展 |

## 10. 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|----------|
| AC-EVT-01 | WebSocket 连接后可订阅 Evaluation 频道 | wscat 测试 |
| AC-EVT-02 | evaluation.started 事件在 Runner 启动时触发 | WebSocket 消息验证 |
| AC-EVT-03 | scenario.completed 事件包含 latency_ms 和 token_count | 消息体校验 |
| AC-EVT-04 | evaluation.progress 的 completed/total 计数正确 | 消息体校验 |
| AC-EVT-05 | 断线重连后不丢失事件（基于序列号续传） | 断线重连测试 |
| AC-EVT-06 | 重复 event_id 被消费者正确去重 | 幂等性测试 |
| AC-EVT-07 | event_log 表记录所有已发出事件 | DB 查询 |
| AC-EVT-08 | 心跳 60s 超时后连接自动断开 | 超时测试 |
