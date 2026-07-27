# Tech Specification — 全局实现规范

> **Depends on**: ./architecture/overview.md, ./architecture/design-principles.md
> **Referenced by**: ./phases/phase-1-foundation.md, ./phases/phase-2-scenario.md, ./phases/phase-3-runner.md, ./phases/phase-4-judge.md
> **ADR**: 0002-conversation-trace-jsonb-storage.md, 0005-architecture-minimal-docs.md

## 1. 目标

定义 AgentEval 全局实现规范：目录结构、数据对象规范、API 返回格式、日志规范、错误码体系、配置系统、中间件。所有 Phase 的实现必须遵守本规范。

> **架构原则**：分层架构、依赖方向、命名约定、SPI/Registry 设计原则等长期稳定约束见 `./architecture/overview.md` 和 `./architecture/design-principles.md`。本文档只包含实现级规范。

## 2. 目录结构

```
src/agenteval/
├── main.py                      # FastAPI 应用入口
├── core/                        # 基础设施（跨层共享）
│   ├── config.py                # 配置加载
│   ├── logging.py               # 日志配置
│   ├── exceptions.py            # 异常基类与错误码
│   ├── response.py              # 统一响应封装
│   ├── database.py              # 异步 DB 引擎与 Session
│   ├── redis.py                 # Redis 连接池
│   └── security.py              # 鉴权工具
├── api/                         # Controller 层
│   └── v1/
│       ├── __init__.py          # 路由注册
│       ├── workspaces.py
│       ├── projects.py
│       ├── datasets.py
│       ├── scenarios.py
│       ├── evaluations.py
│       ├── judges.py
│       ├── traces.py
│       ├── reports.py
│       ├── regressions.py
│       └── plugins.py
├── services/                    # Application 层
│   ├── workspace_service.py
│   ├── dataset_service.py
│   ├── scenario_service.py
│   ├── evaluation_service.py
│   ├── judge_service.py
│   ├── trace_service.py
│   ├── report_service.py
│   └── regression_service.py
├── domain/                      # Domain 层
│   ├── entities/                # 领域实体
│   │   ├── workspace.py
│   │   ├── project.py
│   │   ├── dataset.py
│   │   ├── scenario.py
│   │   ├── conversation.py
│   │   ├── agent_execution.py
│   │   ├── judge_result.py
│   │   ├── trace.py
│   │   ├── metrics.py
│   │   ├── report.py
│   │   └── regression.py
│   ├── value_objects/           # 值对象
│   │   ├── score.py
│   │   ├── trace_span.py
│   │   └── metric_unit.py
│   ├── events/                  # 领域事件
│   │   ├── execution_started.py
│   │   ├── execution_completed.py
│   │   └── judge_completed.py
│   └── enums.py                 # 全局枚举
├── infra/                       # Infrastructure 层
│   ├── models/                  # SQLAlchemy ORM 模型
│   │   ├── base.py
│   │   ├── workspace_model.py
│   │   └── ...
│   ├── repositories/            # 仓储实现
│   │   ├── workspace_repo.py
│   │   └── ...
│   ├── storage/                 # 对象存储
│   │   └── minio_client.py
│   └── tasks/                   # Celery 任务
│       ├── evaluation_task.py
│       └── judge_task.py
├── adapters/                    # Agent Adapter 实现
│   ├── base.py                  # SPI 接口
│   ├── http_adapter.py
│   ├── openai_adapter.py
│   └── custom_adapter.py
├── judges/                      # Judge 实现
│   ├── base.py
│   ├── rule_judge.py
│   ├── llm_judge.py
│   └── embedding_judge.py
├── plugins/                     # 插件系统
│   ├── registry.py
│   └── loader.py
└── schemas/                     # Pydantic DTO/VO
    ├── common.py
    ├── workspace.py
    ├── dataset.py
    ├── scenario.py
    ├── evaluation.py
    ├── judge.py
    ├── trace.py
    └── report.py
```

### 2.2 层间依赖规则

| 层 | 可依赖 | 禁止依赖 |
|----|--------|----------|
| Controller (api/) | Service, Schema | Domain Entity, ORM Model |
| Service (services/) | Domain, Repository 接口, Schema | ORM Model（通过 Repository 隔离） |
| Domain (domain/) | 自身、标准库 | 任何外部框架 |
| Infra (infra/) | Domain 接口 | Controller, Service |

## 3. 数据对象规范

### 3.1 三层对象定义

| 对象类型 | 位置 | 职责 | 命名后缀 |
|----------|------|------|----------|
| Entity | `domain/entities/` | 领域实体，含领域逻辑与不变量 | 无后缀（如 `Scenario`） |
| ORM Model | `infra/models/` | 数据库映射，含表名/列/关系 | `Model` 后缀（如 `ScenarioModel`） |
| DTO (Request) | `schemas/` | API 请求体校验 | `Request` 后缀（如 `CreateScenarioRequest`） |
| VO (Response) | `schemas/` | API 响应体序列化 | `Response` 后缀（如 `ScenarioResponse`） |

### 3.2 转换规则

```
Request (DTO) ──[Service 校验]──> Entity (Domain) ──[Repository]──> Model (ORM)
                                                        │
Response (VO) <──[Service 组装]── Entity (Domain) <──────┘
```

- Controller 只接收 Request、返回 Response
- Service 负责 Entity ↔ Request/Response 转换
- Repository 负责 Entity ↔ ORM Model 转换
- Entity 不含 ORM 注解，不含 Pydantic 注解

### 3.3 公共字段基类

所有 ORM Model 继承 `BaseModel`，包含以下审计字段：

```python
class BaseModel:
    __abstract__ = True
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

软删除规则：查询默认过滤 `deleted_at IS NULL`，通过 `with_deleted=True` 参数可查询已删除记录。

## 4. API 返回结构统一格式

### 4.1 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": { },
  "request_id": "req-550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-07-04T12:00:00.000Z"
}
```

### 4.2 分页响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [ ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  },
  "request_id": "req-...",
  "timestamp": "2026-07-04T12:00:00.000Z"
}
```

### 4.3 错误响应

```json
{
  "code": 40401,
  "message": "Scenario not found",
  "data": null,
  "request_id": "req-...",
  "timestamp": "2026-07-04T12:00:00.000Z",
  "errors": [
    {
      "field": "scenario_id",
      "message": "Scenario with id 'xxx' does not exist"
    }
  ]
}
```

### 4.4 实现规范

```python
# core/response.py
from pydantic import BaseModel
from typing import TypeVar, Generic, Optional
from datetime import datetime

T = TypeVar("T")

class ErrorDetail(BaseModel):
    field: str
    message: str

class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: Optional[T] = None
    request_id: str
    timestamp: datetime
    errors: Optional[list[ErrorDetail]] = None

class PageData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

def success(data: T = None, message: str = "success") -> ApiResponse[T]:
    return ApiResponse(code=0, message=message, data=data, ...)

def paginated(items: list, total: int, page: int, page_size: int) -> ApiResponse[PageData]:
    total_pages = (total + page_size - 1) // page_size
    return success(PageData(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages))
```

## 5. 错误码体系

### 5.1 错误码格式

```
HHHCC
│ │ └─ 两位业务码（01-99）
│ └─── 两位模块码（见下表）
└───── 一位 HTTP 状态码缩写（4=4xx, 5=5xx）
```

### 5.2 模块码

| 模块码 | 模块 | HTTP 前缀 |
|--------|------|-----------|
| 00 | 系统/通用 | 4xx=400xx, 5xx=500xx |
| 01 | Workspace | 4xx=401xx, 5xx=501xx |
| 02 | Project | 4xx=402xx, 5xx=502xx |
| 03 | Dataset | 4xx=403xx, 5xx=503xx |
| 04 | Scenario | 4xx=404xx, 5xx=504xx |
| 05 | Evaluation | 4xx=405xx, 5xx=505xx |
| 06 | Judge | 4xx=406xx, 5xx=506xx |
| 07 | Trace | 4xx=407xx, 5xx=507xx |
| 08 | Report | 4xx=408xx, 5xx=508xx |
| 09 | Regression | 4xx=409xx, 5xx=509xx |
| 10 | Plugin | 4xx=410xx, 5xx=510xx |

### 5.3 通用错误码

| 错误码 | HTTP | 含义 | message |
|--------|------|------|---------|
| 40000 | 400 | 请求参数校验失败 | `Validation failed` |
| 40001 | 400 | JSON 解析失败 | `Invalid JSON body` |
| 40100 | 401 | 未认证 | `Authentication required` |
| 40300 | 403 | 无权限 | `Permission denied` |
| 40400 | 404 | 资源不存在 | `Resource not found` |
| 40900 | 409 | 资源冲突 | `Resource conflict` |
| 42900 | 429 | 请求过于频繁 | `Rate limit exceeded` |
| 50000 | 500 | 内部错误 | `Internal server error` |
| 50200 | 502 | 上游服务错误 | `Upstream service error` |
| 50300 | 503 | 服务不可用 | `Service unavailable` |

### 5.4 异常基类

```python
# core/exceptions.py
class AgentEvalException(Exception):
    """所有业务异常基类"""
    def __init__(self, code: int, message: str, http_status: int = 400,
                 errors: list[dict] | None = None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.errors = errors or []

class NotFoundException(AgentEvalException):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(code=40400, message=f"{resource} not found: {resource_id}", http_status=404)

class ValidationException(AgentEvalException):
    def __init__(self, errors: list[dict]):
        super().__init__(code=40000, message="Validation failed", http_status=400, errors=errors)

class ConflictException(AgentEvalException):
    def __init__(self, resource: str, detail: str):
        super().__init__(code=40900, message=f"{resource} conflict: {detail}", http_status=409)
```

### 5.5 全局异常处理

```python
# main.py 中的异常处理注册
@app.exception_handler(AgentEvalException)
async def business_exception_handler(request: Request, exc: AgentEvalException):
    return JSONResponse(
        status_code=exc.http_status,
        content=ApiResponse(
            code=exc.code,
            message=exc.message,
            data=None,
            request_id=request.state.request_id,
            timestamp=datetime.now(timezone.utc),
            errors=exc.errors or None,
        ).model_dump()
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [{"field": ".".join(str(x) for x in e["loc"]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(
        status_code=400,
        content=ApiResponse(
            code=40000, message="Validation failed", data=None,
            request_id=request.state.request_id,
            timestamp=datetime.now(timezone.utc),
            errors=errors,
        ).model_dump()
    )
```

## 6. 日志规范

### 6.1 日志格式

JSON 结构化日志，每行一条：

```json
{
  "timestamp": "2026-07-04T12:00:00.123Z",
  "level": "INFO",
  "logger": "agenteval.services.evaluation_service",
  "request_id": "req-550e8400",
  "trace_id": "trace-abc123",
  "event": "evaluation.started",
  "message": "Evaluation task started",
  "extra": {
    "evaluation_id": "eval-001",
    "scenario_id": "scn-001",
    "agent_config": "openai-gpt4"
  }
}
```

### 6.2 日志级别

| 级别 | 用途 | 示例 |
|------|------|------|
| DEBUG | 开发调试，生产关闭 | SQL 查询、Adapter 请求体 |
| INFO | 关键业务节点 | 任务启动、完成、状态变更 |
| WARN | 可恢复异常 | 重试触发、超时降级、配额接近上限 |
| ERROR | 不可恢复异常 | 任务失败、数据库连接断开 |
| CRITICAL | 系统级故障 | 服务无法启动、数据损坏 |

### 6.3 关键事件清单

| event | 级别 | 触发点 |
|-------|------|--------|
| `request.received` | INFO | 每个 HTTP 请求入口 |
| `request.completed` | INFO | 每个 HTTP 请求出口（含 status_code, latency_ms） |
| `evaluation.started` | INFO | 评测任务开始 |
| `evaluation.scenario_started` | INFO | 单 Scenario 执行开始 |
| `evaluation.scenario_completed` | INFO | 单 Scenario 执行完成 |
| `evaluation.completed` | INFO | 评测任务完成 |
| `evaluation.failed` | ERROR | 评测任务失败 |
| `judge.started` | INFO | 评分开始 |
| `judge.completed` | INFO | 评分完成 |
| `adapter.request_sent` | DEBUG | 发送给 Agent 的请求 |
| `adapter.response_received` | DEBUG | 收到 Agent 响应 |
| `adapter.retry` | WARN | Agent 调用重试 |
| `adapter.timeout` | ERROR | Agent 调用超时 |

### 6.4 实现规范

```python
# core/logging.py
import structlog

def configure_logging(log_level: str = "INFO", json_output: bool = True):
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# 使用方式
logger = structlog.get_logger("agenteval.services.evaluation_service")
logger.info("evaluation.started", evaluation_id="eval-001", scenario_id="scn-001")
```

## 7. 配置系统设计

### 7.1 配置分层

```
环境变量 (.env)  →  config.yaml (项目级)  →  数据库 (runtime 覆盖)
     高优先级                                        低优先级
```

优先级：环境变量 > config.yaml > 数据库配置 > 默认值。

### 7.2 配置 Schema

```python
# core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class DatabaseConfig(BaseModel):
    url: str = "postgresql+asyncpg://agenteval:agenteval@localhost:5432/agenteval"
    pool_size: int = 10
    max_overflow: int = 20
    pool_recycle: int = 3600
    echo: bool = False

class RedisConfig(BaseModel):
    url: str = "redis://localhost:6379/0"
    max_connections: int = 50

class StorageConfig(BaseModel):
    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket: str = "agenteval"
    secure: bool = False

class CeleryConfig(BaseModel):
    broker_url: str = "redis://localhost:6379/1"
    result_backend: str = "redis://localhost:6379/2"
    task_max_retries: int = 3
    task_default_timeout: int = 300

class EvaluationConfig(BaseModel):
    max_concurrent_scenarios: int = 10
    default_timeout_seconds: int = 120
    default_retry_count: int = 2
    default_retry_delay_seconds: int = 5

class Settings(BaseSettings):
    # 基础
    app_name: str = "AgentEval"
    env: str = Field(default="development", pattern="^(development|staging|production)$")
    debug: bool = False
    secret_key: str = "change-me-in-production"
    api_prefix: str = "/api/v1"

    # 子配置
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    storage: StorageConfig = StorageConfig()
    celery: CeleryConfig = CeleryConfig()
    evaluation: EvaluationConfig = EvaluationConfig()

    # 日志
    log_level: str = "INFO"
    log_json: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_prefix="AGENTEVAL_",
    )

settings = Settings()
```

### 7.3 环境变量映射

| 环境变量 | 对应字段 | 默认值 |
|----------|----------|--------|
| `AGENTEVAL_ENV` | `settings.env` | `development` |
| `AGENTEVAL_DEBUG` | `settings.debug` | `false` |
| `AGENTEVAL_SECRET_KEY` | `settings.secret_key` | `change-me` |
| `AGENTEVAL_DATABASE__URL` | `settings.database.url` | PG 本地连接串 |
| `AGENTEVAL_REDIS__URL` | `settings.redis.url` | `redis://localhost:6379/0` |
| `AGENTEVAL_EVALUATION__MAX_CONCURRENT_SCENARIOS` | `settings.evaluation.max_concurrent_scenarios` | `10` |

## 8. 中间件规范

### 8.1 Request ID 中间件

每个请求自动注入 `request_id`，若请求头无 `X-Request-ID` 则自动生成 UUID。

```python
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req-{uuid4()}"
    request.state.request_id = request_id
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

### 8.2 请求日志中间件

记录所有 HTTP 请求的 method、path、status、latency。

```python
@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    latency_ms = (time.monotonic() - start) * 1000
    logger.info("request.completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency_ms=round(latency_ms, 2))
    return response
```

## 9. 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|----------|
| AC-00-01 | `GET /api/v1/health` 返回 `{"code":0,"message":"success","data":{"status":"ok"}}` | curl 验证 |
| AC-00-02 | 请求无 `X-Request-ID` 头时，响应头自动包含生成的 `X-Request-ID` | curl 验证 |
| AC-00-03 | 请求参数校验失败返回 code=40000 且 errors 数组非空 | POST 非法 JSON |
| AC-00-04 | 未捕获异常返回 code=50000 且 HTTP 500 | 触发内部错误 |
| AC-00-05 | 日志为 JSON 格式且包含 request_id 字段 | 检查日志输出 |
| AC-00-06 | `AGENTEVAL_ENV=production` 时 `settings.debug` 为 `False` | 单元测试 |
| AC-00-07 | 软删除记录默认不返回，`with_deleted=True` 时可返回 | 集成测试 |
| AC-00-08 | 分页接口返回 `total_pages` 正确计算 | 单元测试 |

## 10. 数据存储说明

> **Conversation 与 Trace 当前采用 JSONB 存储，未来可根据实际数据规模和查询需求演进为独立关系模型。**
>
> 详见 ADR-0002。
