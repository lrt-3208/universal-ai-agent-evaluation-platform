# Design Principles

> **Depends on**: ./overview.md
> **Referenced by**: ../phases/phase-1-foundation.md, ../phases/phase-3-runner.md, ../phases/phase-4-judge.md, ../phases/phase-7-plugin.md

## 1. 定位

本文档记录 AgentEval 系统长期稳定的、具有全局约束性的架构设计原则。所有 Phase 的实现必须遵守这些原则。

**与 ADR 的关系**：本文档只记录"必须遵守的规则"（如分层依赖方向）。具体权衡后的方案选择（如为什么用 JSONB 而非关系表）记录在 `../decisions/` 中，不在本文档范围内。

## 2. 分层依赖规则

| 规则 | 说明 |
|------|------|
| 依赖方向 | Controller → Service → Domain → Infra，禁止反向依赖 |
| Domain 隔离 | Domain 层不依赖 FastAPI / SQLAlchemy / Celery 等框架 |
| Service 编排 | Service 层负责事务边界和领域调度，不直接处理 HTTP 请求 |
| Controller 精简 | Controller 层只做请求校验、路由、响应序列化，不含业务逻辑 |
| Infra 实现 | Infra 层实现 Domain 层定义的接口（Repository 等），不定义业务规则 |

## 3. 命名规范

### 3.1 跨层字段映射

同一概念在不同层使用不同名称时，必须遵循以下映射：

| 概念 | Domain Entity | ORM Model | DTO Request | VO Response |
|------|---------------|-----------|-------------|-------------|
| 场景输入 | `input` (dict) | `input_data` (JSONB) | `input` (dict) | `input` (dict) |
| 期望输出 | `expected` (dict) | `expected_data` (JSONB) | `expected` (dict) | `expected` (dict) |
| 评测配置 | `config` (dict) | `config_data` (JSONB) | `config` (dict) | `config` (dict) |

**规则**：ORM Model 中 JSONB 字段使用 `_data` 后缀，避免与 Python 保留字冲突。其他层保持业务语义命名。

### 3.2 通用命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 类名 | PascalCase | `EvaluationService` |
| 方法名 | snake_case | `create_evaluation` |
| 常量 | UPPER_SNAKE_CASE | `MAX_CONCURRENT_EXECUTIONS` |
| 数据库表 | snake_case 复数 | `evaluations`, `scenario_executions` |
| 枚举值 | UPPER_SNAKE_CASE | `EvaluationStatus.RUNNING` |
| API 路径 | kebab-case | `/api/v1/scenario-executions` |

### 3.3 字段变更检查清单

修改任何领域实体字段时，必须同步检查以下四处：

- [ ] Domain Entity (`domain/entities/*.py`)
- [ ] ORM Model (`infra/models/*.py`)
- [ ] DTO Request (`api/dto/*.py`)
- [ ] VO Response (`api/vo/*.py`)

## 4. SPI / Registry 设计原则

### 4.1 最小接口原则（Minimal Interface Principle）

- SPI 基础接口只包含所有实现都必须提供的方法
- 不是所有实现都需要的能力，通过 Capability 声明或扩展接口提供，不放入基础接口
- 基础接口应长期保持稳定，新能力通过声明式机制扩展，不修改基础接口

### 4.2 声明式 Capability

- Adapter 能力通过 `capabilities: set[str]` 声明式模型表达
- 使用可扩展集合（`set[str]`），不使用固定字段列表
- Runner 根据 Capability 集合决定执行策略
- 新增能力只需增加标识字符串，不修改接口定义

### 4.3 Registry 统一模式

所有 SPI 遵循统一的 Registry 模式：

```python
class Registry(Generic[T]):
    def register(self, name: str, impl: type[T]) -> None: ...
    def unregister(self, name: str) -> None: ...
    def create(self, name: str, config: dict) -> T: ...
    def list(self) -> list[str]: ...
```

- 内置实现通过 Registry 静态注册（"内置插件"概念）
- 外部实现通过 Plugin 系统动态注册，使用同一个 `register()` 方法
- Registry 接口不因内置/外部来源不同而变化

### 4.4 Open/Closed 原则

- 新增 Judge / Adapter / 指标类型只需注册新实现，不修改已有代码
- ScoreDiffer 等分析组件基于动态指标集合工作，不维护固定指标白名单
- 后续 Phase 不修改前序 Phase 已交付的代码

## 5. 扩展点设计原则

| 原则 | 说明 |
|------|------|
| 抽象类预留扩展 | 每个 SPI 在 Phase 1 定义抽象类，后续 Phase 实现具体类 |
| Phase 不可变性 | 后续 Phase 不修改前序 Phase 已交付代码，只通过注册新实现扩展 |
| 契约优先 | Contract 修改优先，Phase 仅同步引用，不重复定义接口 |
| 内置 = 插件 | 内置实现与外部插件通过同一 Registry 注册，无代码路径差异 |

## 6. DRY 与一致性约束

### 6.1 单一定义来源

- 接口定义只在 `contracts/` 中定义一次，Phase 文档引用不重复
- 领域模型只在 `contracts/domain-model.md` 中定义一次
- 指标定义只在 `contracts/metrics-definition.md` 中定义一次
- 错误码只在 `tech-spec.md` 中定义一次

### 6.2 术语统一

同一概念跨所有文档使用统一术语：

| 统一术语 | 禁止变体 |
|----------|----------|
| AgentExecution | AgentResult, ExecutionResult |
| ScenarioExecution | ScenarioRun, TestExecution |
| JudgeResult | ScoreResult, EvaluationResult |
| TraceSpan | Span, TraceNode |
| MetricScore | Metric, Score |

## 7. Trace 管控原则

- Trace 完全由 Runner / Middleware 负责采集
- Adapter 不感知 Trace，不接收 TraceCollector 参数
- 基础 Trace（入口/出口时间、请求/响应快照）由 Runner 自动采集
- 衍生指标通过 Derived Metric Provider 按需计算，不暴露 Trace 内部结构
