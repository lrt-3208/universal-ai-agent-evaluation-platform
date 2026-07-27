# Error Model Contract — 错误模型契约

> **Depends on**: `domain-model.md`  
> **Referenced by**: `../tech-spec.md`, `../phases/phase-1-foundation.md`, `../phases/phase-2-scenario.md`, `../phases/phase-3-runner.md`, `../phases/phase-4-judge.md`, `../phases/phase-5-report.md`, `../phases/phase-6-regression.md`, `../phases/phase-7-plugin.md`  
> **ADR**: `../decisions/0008-error-model-contract.md`

## 1. 定位

定义 AgentEval 系统的统一错误分类、错误码区间、响应格式和传播规则。本契约是 REST API、CLI、WebSocket、Plugin、Runtime 的唯一错误模型真相——各层不得自定义错误格式。

> **与 Domain Model 的关系**：Domain Model §18.5 定义了字段级验证错误码 (40001-40015)，本契约将其纳入统一体系并扩展到全部错误类别。

## 2. 错误码格式

```
  ┌─── HTTP Status (3 digits)
  │  ┌── Domain Code (2 digits)
  │  │ ┌ Sequence (2 digits, per domain per status)
  │  │ │
404 01
```

| 段 | 取值 | 说明 |
|----|------|------|
| HTTP Status | `400` / `404` / `409` / `500` | HTTP 状态码前缀 |
| Domain Code | `00`-`99` | 子系统编号（见 §3） |
| Sequence | `01`-`99` | 同 domain + status 内的序号 |

**示例**：`40403` = HTTP 404 (Not Found) + Domain 04 (Dataset) + 序号 03

## 3. 错误分类与码段分配

### 3.1 Domain Code 分配

| Domain Code | 子系统 | 4xx 码段 | 5xx 码段 |
|-------------|--------|----------|----------|
| 00 | Validation / Foundation | 40001-40099 | 50001-50099 |
| 03 | Dataset / Scenario / DSL | 40301-40399 | 50301-50399 |
| 04 | Not Found (跨域共享) | 40401-40499 | — |
| 05 | Runner / Adapter | 40501-40599 | 50501-50599 |
| 06 | Judge | 40601-40699 | 50601-50699 |
| 08 | Report / Trace | 40801-40899 | 50801-50899 |
| 09 | Conflict (跨域共享) | 40901-40999 | — |
| 10 | Plugin | 41001-41099 | 51001-51099 |

> **跨域共享码段**：`404xx` (Not Found) 和 `409xx` (Conflict) 跨所有子系统使用，序号全局递增。

### 3.2 错误类别定义

| 错误类别 | 对应异常类 | 码段 | retryable | HTTP | log_level | 说明 |
|----------|-----------|------|-----------|------|-----------|------|
| **ValidationError** | `ValidationError` | 400xx | No | 400 | WARN | 字段校验失败、格式错误、枚举不匹配 |
| **NotFoundError** | `NotFoundException` | 404xx | No | 404 | WARN | 资源不存在 |
| **ConflictError** | `ConflictException` | 409xx | No | 409 | WARN | 唯一约束冲突、状态冲突 |
| **ConfigurationError** | `ConfigurationError` | 405xx / 406xx | No | 400 | ERROR | Adapter/Judge 配置无效 |
| **TimeoutError** | `TimeoutError` | 505xx | **Yes** | — | WARN | Agent 调用超时、评测级超时 |
| **AdapterError** | `AdapterError` | 505xx | **Yes** | — | ERROR | Agent 调用失败（网络/协议/解析） |
| **JudgeError** | `JudgeError` | 506xx | **Yes** | — | ERROR | LLM 调用失败、Embedding 服务不可用 |
| **PluginLoadError** | `PluginLoadError` | 510xx | No | 500 | ERROR | 插件 import/初始化失败 |
| **PermissionError** | `PermissionError` | 403xx | No | 403 | WARN | 鉴权失败、权限不足 (MAY, 待 Auth Provider 实现) |
| **InternalError** | `AgentEvalException` | 500xx | No | 500 | ERROR | 未分类的内部错误 |

### 3.3 retryable 规则

| retryable | 含义 | 客户端行为 | 示例 |
|-----------|------|-----------|------|
| **No** | 不可重试 | 修正请求后重发 | ValidationError, NotFoundError, ConflictError |
| **Yes** | 可重试 | 指数退避重试 (max 3) | TimeoutError, AdapterError, JudgeError |

> Runner 内部重试由 `config.retry_count` 控制，不计入客户端 retryable。

## 4. 统一错误响应格式

### 4.1 REST API 错误响应

```json
{
    "code": 40403,
    "message": "Dataset not found: ds-uuid",
    "detail": {
        "resource_type": "Dataset",
        "resource_id": "ds-uuid"
    },
    "retryable": false,
    "request_id": "req-uuid"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | int | MUST | 5 位错误码 |
| message | str | MUST | 面向用户的错误消息（模板填充后） |
| detail | dict | SHOULD | 错误上下文（资源类型、ID、字段名等） |
| retryable | bool | MUST | 是否可重试 |
| request_id | str | MUST | X-Request-ID 头的值 |

### 4.2 WebSocket 错误消息

```json
{
    "action": "error",
    "code": 40404,
    "message": "Evaluation not found: eval-uuid",
    "retryable": false
}
```

### 4.3 Event Payload 中的错误

当 Core Event `system.error` 或 Extension Event 携带错误信息时，payload 使用以下结构：

```json
{
    "error_type": "AdapterError",
    "error_code": 50502,
    "error_message": "Agent call failed: Connection refused",
    "retryable": true,
    "context": {
        "scenario_id": "scn-uuid",
        "adapter_type": "openai"
    }
}
```

### 4.4 日志格式

```
ERROR [request_id=req-uuid] [error_code=50502] [error_type=AdapterError] [retryable=true]
    Agent call failed: Connection refused
    context: scenario_id=scn-uuid, adapter_type=openai, endpoint=https://api.openai.com/v1
```

## 5. 错误码完整索引

### 5.1 ValidationError (400xx, HTTP 400, retryable=No)

| 错误码 | 字段/场景 | message 模板 | 来源 |
|--------|----------|-------------|------|
| 40001 | Workspace.slug | `Invalid slug: must match ^[a-z0-9-]+$, 1-64 chars` | Domain Model §18.5 |
| 40002 | Project.slug | `Invalid slug: must match ^[a-z0-9-]+$, 1-64 chars, unique per workspace` | Domain Model §18.5 |
| 40003 | Dataset.version | `Invalid version: must be semantic version (e.g. "1.0.0")` | Domain Model §18.5 |
| 40004 | Dataset.format | `Invalid format: must be yaml | json | csv` | Domain Model §18.5 |
| 40005 | Scenario.external_id | `Invalid external_id: must match ^[A-Za-z0-9_-]+$, 1-64 chars, unique per dataset` | Domain Model §18.5 |
| 40006 | Scenario.priority | `Invalid priority: must be 0-100` | Domain Model §18.5 |
| 40007 | Evaluation.config.max_concurrent | `Invalid max_concurrent: must be 1-100` | Domain Model §18.5 |
| 40008 | Evaluation.config.timeout_seconds | `Invalid timeout_seconds: must be 1-3600` | Domain Model §18.5 |
| 40009 | MetricScore.score | `Invalid score: must be 0.0 <= score <= max_score` | Domain Model §18.5 |
| 40010 | MetricScore.weight | `Invalid weight: must be >= 0.0` | Domain Model §18.5 |
| 40011 | JudgeResult.overall_score | `Invalid overall_score: must be NULL or 0.0-1.0` | Domain Model §18.5 |
| 40012 | Report.format | `Invalid format: must be json | html` | Domain Model §18.5 |
| 40013 | Message.role | `Invalid role: must be user | assistant | system | tool` | Domain Model §18.5 |
| 40014 | ToolCall.status | `Invalid status: must be success | error | timeout` | Domain Model §18.5 |
| 40015 | TraceSpan.status | `Invalid status: must be ok | error | timeout` | Domain Model §18.5 |

### 5.2 Dataset / Scenario / DSL (403xx, HTTP 400, retryable=No)

| 错误码 | 场景 | message 模板 |
|--------|------|-------------|
| 40301 | DSL 解析失败 | `DSL parse error: {detail}` |
| 40302 | DSL 校验失败 | `DSL validation failed: {detail}` |
| 40303 | 导入场景超限 | `Dataset import exceeds {limit} scenario limit` |

### 5.3 NotFoundError (404xx, HTTP 404, retryable=No)

| 错误码 | 资源 | message 模板 |
|--------|------|-------------|
| 40401 | Workspace | `Workspace not found: {id}` |
| 40402 | Project | `Project not found: {id}` |
| 40403 | Dataset | `Dataset not found: {id}` |
| 40404 | Scenario / Evaluation | `{Resource} not found: {id}` |
| 40405 | Evaluation | `Evaluation not found: {id}` |
| 40406 | ScenarioExecution | `ScenarioExecution not found: {id}` |
| 40407 | Trace | `Trace not found: {id}` |
| 40408 | Report | `Report not found: {id}` |
| 40409 | Evaluation (Regression) | `{Baseline/Target} evaluation not found: {id}` |
| 40410 | Regression | `Regression not found: {id}` |
| 40411 | Plugin | `Plugin not found: {name}` |

### 5.4 ConfigurationError (405xx / 406xx, HTTP 400, retryable=No)

| 错误码 | 场景 | message 模板 |
|--------|------|-------------|
| 40501 | Dataset 无场景 | `Dataset has no scenarios` |
| 40502 | Adapter 类型不支持 | `Unsupported adapter type: {type}` |
| 40503 | Adapter 配置无效 | `Invalid adapter config: {detail}` |
| 40601 | Judge 类型不支持 | `Unknown judge type: {type}` |
| 40602 | Judge 配置无效 | `Invalid judge config: {detail}` |
| 40801 | 报告格式不支持 | `Unsupported report format: {format}` |
| 41002 | Plugin manifest 校验失败 | `Plugin manifest invalid: {detail}` |
| 41003 | Plugin 配置校验失败 | `Plugin config invalid: {detail}` |
| 41004 | Plugin 类型不支持 | `Unsupported plugin type: {type}` |

### 5.5 ConflictError (409xx, HTTP 409, retryable=No)

| 错误码 | 场景 | message 模板 |
|--------|------|-------------|
| 40901 | Workspace slug 重复 | `Workspace slug already exists: {slug}` |
| 40902 | Project slug 重复 | `Project slug already exists in workspace: {slug}` |
| 40903 | Dataset 版本冲突 | `Dataset {name} v{version} already exists` |
| 40904 | Scenario external_id 冲突 | `Scenario external_id '{id}' already exists in dataset` |
| 40905 | 评测已取消 | `Evaluation is cancelled` |
| 40906 | 评测未完成不可评分 | `Evaluation is not in SCORING state` |
| 40907 | 评测状态冲突（通用） | `Evaluation status conflict: current={status}, expected={expected}` |
| 40908 | 评测未完成不可生成报告 | `Evaluation not completed, cannot generate report` |
| 40909 | 回归评测未完成 | `Evaluation not completed` |
| 40910 | Dataset 不一致 | `Evaluations must use the same dataset` |
| 41005 | Plugin 已启用 | `Plugin already enabled: {name}` |

### 5.6 Internal Error (500xx, HTTP 500, retryable=No)

| 错误码 | 场景 | message 模板 |
|--------|------|-------------|
| 50001 | DB 连接失败 | `Database connection failed` |
| 50002 | Redis 连接失败 | `Redis connection failed` |
| 50099 | 未分类内部错误 | `Internal error: {detail}` |

### 5.7 TimeoutError (505xx, retryable=Yes)

| 错误码 | 场景 | message 模板 | log_level |
|--------|------|-------------|-----------|
| 50501 | Agent 调用超时 | `Agent call timeout after {timeout}s` | WARN |
| 50503 | 评测级超时 | `Evaluation timeout: Celery task terminated` | WARN |

### 5.8 AdapterError (505xx, retryable=Yes)

| 错误码 | 场景 | message 模板 |
|--------|------|-------------|
| 50502 | Agent 调用失败 | `Agent call failed: {detail}` |

### 5.9 JudgeError (506xx, retryable=Yes)

| 错误码 | 场景 | message 模板 |
|--------|------|-------------|
| 50601 | LLM Judge 调用失败 | `LLM Judge call failed: {detail}` |
| 50602 | Embedding 服务不可用 | `Embedding service unavailable: {detail}` |

### 5.10 Report Internal Error (508xx, retryable=No)

| 错误码 | 场景 | message 模板 |
|--------|------|-------------|
| 50801 | 对象存储上传失败 | `Report storage upload failed: {detail}` |
| 50802 | 模板渲染失败 | `Report template render failed: {detail}` |

### 5.11 PluginLoadError (510xx, HTTP 500, retryable=No)

| 错误码 | 场景 | message 模板 |
|--------|------|-------------|
| 51001 | 插件加载失败 | `Plugin load error: {detail}` |
| 51002 | 插件初始化失败 | `Plugin initialization error: {detail}` |

## 6. 错误传播规则

### 6.1 层间传播

```
Adapter / Judge / Plugin
    ↓ (抛出原生异常)
Service Layer
    ↓ (捕获 + 包装为 AgentEvalException 子类)
    ↓ (记录 error_code + context)
API Layer / WebSocket / Event
    ↓ (序列化为统一响应格式)
客户端
```

| 源层 | 目标层 | 规则 |
|------|--------|------|
| Adapter | Runner | Adapter 原生异常 → 包装为 AdapterError (50502) 或 TimeoutError (50501) |
| Judge | JudgeService | Judge 原生异常 → 包装为 JudgeError (50601/50602) |
| Plugin | PluginLoader | Plugin 原生异常 → 包装为 PluginLoadError (51001/51002) |
| Service | API | Service 异常直接映射为 HTTP 响应 |
| 任何层 | Event | 异常同时触发 `system.error` Core Event |

### 6.2 不可丢失上下文

包装异常时 **MUST** 保留原始异常链：

```python
raise AdapterError(
    code=50502,
    message=f"Agent call failed: {e}",
    context={"adapter_type": "openai", "endpoint": "..."}
) from e  # 保留原始异常链
```

### 6.3 不暴露内部细节

- 5xx 错误的 `message` **MUST NOT** 包含堆栈信息、SQL 语句、内部路径
- `detail` 字段 **MAY** 包含资源 ID 和错误类型，但不包含内部实现细节
- 完整堆栈信息只写入日志，不返回客户端

## 7. 异常类层次结构

```python
# core/exceptions.py

class AgentEvalException(Exception):
    """所有 AgentEval 异常的基类"""
    code: int
    message: str
    retryable: bool = False
    detail: dict = {}

class ValidationError(AgentEvalException): ...
class NotFoundException(AgentEvalException): ...
class ConflictException(AgentEvalException): ...
class ConfigurationError(AgentEvalException): ...
class TimeoutError(AgentEvalException):
    retryable = True
class AdapterError(AgentEvalException):
    retryable = True
class JudgeError(AgentEvalException):
    retryable = True
class PluginLoadError(AgentEvalException): ...
class PermissionError(AgentEvalException): ...  # MAY, 待 Auth Provider
class InternalError(AgentEvalException): ...
```

## 8. MUST / SHOULD / MAY 规范

| 规范级别 | 要求 |
|----------|------|
| **MUST** | 错误码 5 位格式、Domain Code 分配、统一响应格式、异常类层次、retryable 标记、异常链保留、5xx 不暴露内部细节 |
| **SHOULD** | detail 字段包含资源类型+ID、日志包含 request_id + error_code |
| **MAY** | PermissionError (403xx) 待 Auth Provider 实现后启用 |

## 9. 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|----------|
| AC-ERR-01 | 所有 API 错误响应包含 code/message/retryable/request_id | 响应体校验 |
| AC-ERR-02 | 4xx 错误不包含堆栈信息 | 安全扫描 |
| AC-ERR-03 | retryable=true 的错误可被 Runner 自动重试 | 集成测试 |
| AC-ERR-04 | 异常链 (`from e`) 在日志中可见 | 日志检查 |
| AC-ERR-05 | 新增错误码不与现有码段冲突 | CI 脚本检查 |
| AC-ERR-06 | system.error Event 携带 error_code 和 error_type | 事件体校验 |
| AC-ERR-07 | WebSocket 错误消息格式与 REST 一致 | wscat 测试 |
| AC-ERR-08 | 各 Phase 的异常设计表与本契约无冲突 | 文档审查 |
