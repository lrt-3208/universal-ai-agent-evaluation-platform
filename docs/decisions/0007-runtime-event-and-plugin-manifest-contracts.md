# ADR 0007: Runtime Event Contract 与 Plugin Manifest Contract

| 字段 | 值 |
|------|-----|
| Status | Accepted |
| Date | 2026-07-04 |
| Context | Contract Freeze 评审 + 稳定性优化评审 |

## Context

Contract Freeze 评审指出契约完备度为 8.5/10，建议补充两份契约。初版完成后，稳定性优化评审提出 5 条改进建议（评分 9.8/10），核心诉求是确保契约冻结后的长期演进稳定性。

## Decision

### 1. 新增 `contracts/runtime-event-contract.md`（协议无关三层架构）

- **Layer 1: Event Schema (MUST)**：统一 EventEnvelope 信封 + 8 个 Core Event（冻结）+ Extension Event（MAY，可扩展不修改契约）
- **Layer 2: Delivery Semantics (MUST)**：FIFO 顺序保证 + event_id 幂等去重 + event_log 持久化表 + 保留策略
- **Layer 3: Transport Bindings (MAY)**：WebSocket（MVP 实现）、SSE / Webhook / MQ（未来 ADR 新增）

关键设计：Contract 定义 Event，不定义 Transport。新增 Transport Binding 不修改 Event Schema。Core Event 从 30+ 收缩为 8 个跨框架通用事件。

### 2. 新增 `contracts/plugin-manifest-contract.md`（Schema 优先 + Capability 引用）

- **JSON Schema 为主定义**（Draft 2020-12），YAML / JSON 均为合法实例
- **Capabilities 引用各 SPI**：adapter 引用 `adapter-spi.md` 的 `set[str]` Capability，judge 引用 `judge-spi.md` 的 supported_metrics + judge_type，不在 Manifest 中重复维护
- 完整加载流程：Discovery → Parse → Validate → Import → Register → Lifecycle → Ready

### 3. Domain Model 增加 Source of Truth 原则

Domain Model 为唯一字段真相源。DTO / ORM / VO / DSL / API / Event Payload 中的同名字段不得冲突，差异必须在映射层显式声明。

## Rationale

- **协议无关**：Event Schema 与 Transport 解耦，未来切换 Kafka / RabbitMQ 不修改 Contract
- **Core Event 收缩**：8 个跨框架通用事件冻结，Extension Event 按需添加，避免 30+ 事件随 Agent 框架差异频繁变更
- **Schema 优先**：JSON Schema 为主定义，plugin.yaml / plugin.json / 数据库 / HTTP API 共享同一 Schema，不因存储格式差异导致校验逻辑分叉
- **Capability 不重复**：Plugin Manifest 引用各 SPI 的 Capability 定义，避免双边漂移
- **Source of Truth**：Domain Model 作为字段真相源，防止 AI/开发者在 DTO 层私自加字段而忘记同步

## Consequences

- 新增 2 份契约文档 + 1 条 Domain Model 原则
- contracts/ 目录从 5 份增至 7 份
- Phase 3 Runner 需在 8 个 Core Event 触发点发射事件
- Phase 7 Plugin Loader 使用 JSON Schema 校验 plugin.yaml
- Phase 1 Alembic 迁移需创建 event_log 表
- 所有投影层（DTO/ORM/API）字段变更必须先在 Domain Model 定义

## Related

- `../contracts/runtime-event-contract.md`
- `../contracts/plugin-manifest-contract.md`
- `../contracts/domain-model.md` (Source of Truth 原则)
- `../contracts/adapter-spi.md` (Capability 引用源)
- `../contracts/judge-spi.md` (Capability 引用源)
- `../phases/phase-3-runner.md` (Core Event 发射)
- `../phases/phase-7-plugin.md` (Manifest 加载)
- Supersedes: 无
- Superseded by: 无
# ADR 0007: Runtime Event Contract 与 Plugin Manifest Contract

| 字段 | 值 |
|------|-----|
| Status | Accepted |
| Date | 2026-07-04 |
| Context | Contract Freeze 评审 |

## Context

Contract Freeze 评审指出契约完备度为 8.5/10，建议补充两份契约：

1. **Runtime Event Contract**：系统缺少运行时事件的统一定义。WebSocket 实时推送、Celery 任务状态同步、审计日志各自定义事件格式，缺乏一致性。需要统一的事件类型、Payload 结构、交付机制和顺序保证。

2. **Plugin Manifest Contract**：Phase 7 Plugin System 描述了插件生命周期管理，但缺少插件清单文件的标准格式。Loader 需要知道如何发现、校验、加载外部插件，必须有明确的 manifest schema。

## Decision

### 1. 新增 `contracts/runtime-event-contract.md`

定义统一事件信封（EventEnvelope）、7 个事件域共 30+ 种事件类型、WebSocket 频道设计、事件顺序保证（同资源有序、跨资源无序、幂等去重）、事件持久化（event_log 表 + 保留策略）、Webhook 扩展（MAY）。

### 2. 新增 `contracts/plugin-manifest-contract.md`

定义 `plugin.yaml` 清单格式：api_version、metadata、type（5 种插件类型）、entry_point、capabilities（按 type 分化）、config_schema（JSON Schema 子集）、dependencies、permissions、lifecycle 钩子、compatibility。完整加载流程：Discovery → Parse → Validate → Import → Register → Lifecycle → Ready。

## Rationale

- **统一事件源**：WebSocket / Webhook / 审计日志共用 EventEnvelope，避免多套格式维护成本
- **Plugin Manifest 先行**：manifest schema 是 Loader 的实现契约，缺少它则 Phase 7 Task 7.1-7.2 无法启动
- **MAY 标注**：Webhook 和 permissions 强制执行均为 MAY，不阻塞 MVP

## Consequences

- 新增 2 份契约文档，contracts/ 目录从 5 份增至 7 份
- Phase 3 Runner 需在关键节点发射事件（evaluation.started / scenario.completed 等）
- Phase 7 Plugin Loader 需按 manifest schema 校验插件包
- event_log 表需在 Phase 1 Alembic 迁移中创建

## Related

- `../contracts/runtime-event-contract.md`
- `../contracts/plugin-manifest-contract.md`
- `../phases/phase-3-runner.md` (事件发射)
- `../phases/phase-7-plugin.md` (Manifest 加载)
- Supersedes: 无
- Superseded by: 无
