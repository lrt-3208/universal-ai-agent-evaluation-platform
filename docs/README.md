# AgentEval — 通用 AI Agent 对话评测平台

## 文档目录结构（四层）

```
docs/
├── README.md                              # 本文件 — 导航入口
├── tech-spec.md                           # 全局实现规范（目录结构、命名、错误码、日志、配置）
│
├── architecture/                          # 架构原则（长期稳定）
│   ├── overview.md                        # 系统架构概览 + 文档导航
│   └── design-principles.md               # 设计原则与约束
│
├── contracts/                             # 接口契约（SPI 定义、领域模型、DSL）
│   ├── domain-model.md                    # 核心领域模型（字段级定义 + DB 约束）
│   ├── adapter-spi.md                     # Agent Adapter SPI 契约
│   ├── judge-spi.md                       # Judge + LLMClient SPI 契约
│   ├── scenario-dsl.md                    # Scenario DSL 规范
│   ├── metrics-definition.md              # 评测指标体系
│   ├── runtime-event-contract.md          # 运行时事件契约（Event Schema + Delivery + Transport）
│   ├── plugin-manifest-contract.md        # 插件清单契约（JSON Schema 主定义）
│   └── error-model-contract.md            # 错误模型契约（错误码 + 响应格式 + 传播规则）
│
├── phases/                                # 实现指南（每个 Phase 包含 Task 分解）
│   ├── phase-1-foundation.md              # Phase 1: Core Foundation
│   ├── phase-2-scenario.md                # Phase 2: Scenario System
│   ├── phase-3-runner.md                  # Phase 3: Evaluation Engine
│   ├── phase-4-judge.md                   # Phase 4: Judge System
│   ├── phase-5-report.md                  # Phase 5: Trace & Report
│   ├── phase-6-regression.md              # Phase 6: Regression System
│   └── phase-7-plugin.md                  # Phase 7: Plugin System
│
└── decisions/                             # ADR（架构决策记录，不可变）
    ├── README.md                          # ADR 索引 + 模板 + 规则
    ├── 0001-adapter-spi-minimal-interface.md
    ├── 0002-conversation-trace-jsonb-storage.md
    ├── 0003-plugin-concept-frontload.md
    ├── 0004-llm-client-for-judge.md
    ├── 0005-architecture-minimal-docs.md
    ├── 0006-adapter-spi-contract-doc.md
    ├── 0007-runtime-event-and-plugin-manifest-contracts.md
    └── 0008-error-model-contract.md
```

## 阅读路径

| 序号 | 文档 | 角色 | 依赖前置 |
|------|------|------|----------|
| 0 | `architecture/overview.md` | 架构全景 + 导航 | 无 |
| 1 | `architecture/design-principles.md` | 设计约束 | 0 |
| 2 | `tech-spec.md` | 全局实现规范 | 0, 1 |
| 3 | `contracts/domain-model.md` | 领域模型字典 | 2 |
| 4 | `contracts/adapter-spi.md` | Adapter SPI 契约 | 1, 3 |
| 5 | `contracts/judge-spi.md` | Judge + LLMClient SPI 契约 | 1, 3 |
| 6 | `contracts/scenario-dsl.md` | 场景 DSL 规范 | 3 |
| 7 | `contracts/metrics-definition.md` | 指标体系 | 3, 5 |
| 7.5 | `contracts/runtime-event-contract.md` | 运行时事件契约 | 3 |
| 7.6 | `contracts/plugin-manifest-contract.md` | 插件清单契约 | 4, 5 |
| 7.7 | `contracts/error-model-contract.md` | 错误模型契约 | 3 |
| 8 | `phases/phase-1-foundation.md` | Phase 1 实现 | 2, 3 |
| 9 | `phases/phase-2-scenario.md` | Phase 2 实现 | 3, 6, 8 |
| 10 | `phases/phase-3-runner.md` | Phase 3 实现 | 3, 4, 7.5, 8, 9 |
| 11 | `phases/phase-4-judge.md` | Phase 4 实现 | 3, 5, 7, 7.5, 10 |
| 12 | `phases/phase-5-report.md` | Phase 5 实现 | 3, 10, 11 |
| 13 | `phases/phase-6-regression.md` | Phase 6 实现 | 7.5, 10, 11, 12 |
| 14 | `phases/phase-7-plugin.md` | Phase 7 实现 | 4, 5, 7.6, 8 |

## 技术选型（全局约束）

| 维度 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | AI 生态完善，类型注解支持好 |
| Web 框架 | FastAPI 0.110+ | 异步原生、自动 OpenAPI 文档、Pydantic v2 集成 |
| 数据库 | PostgreSQL 16 | JSONB 支持、GIN 索引、行级安全 |
| ORM | SQLAlchemy 2.0 (async) | 异步支持成熟、类型友好 |
| 缓存 | Redis 7 | 任务队列状态、分布式锁、Trace 缓冲 |
| 任务队列 | Celery 5.3 + Redis broker | 异步评测任务执行 |
| 对象存储 | MinIO / S3 兼容 | Dataset 文件、Report HTML、Trace dump |
| 前端 | React 18 + Vite + TypeScript | 组件生态丰富、类型安全 |
| 容器化 | Docker + Docker Compose | 开发环境一致 |

## Phase 概览

| Phase | 名称 | 核心交付物 | 验收里程碑 |
|-------|------|-----------|----------|
| 1 | Core Foundation | 项目骨架、Workspace/Project CRUD、SPI Registry、LLMClient | `GET /api/v1/health` 返回 200 |
| 2 | Scenario System | Dataset/Scenario CRUD、Scenario DSL 解析器 | DSL YAML 可解析并持久化 |
| 3 | Evaluation Engine | Runner、Adapter SPI、并发执行、基础 Trace | 单个 Scenario 端到端执行 |
| 4 | Judge System | Rule/LLM Judge、Score Aggregation | 对 AgentExecution 产出 JudgeResult |
| 5 | Trace & Report | Trace Tree、Timeline、JSON+HTML Report | 可生成 HTML 报告 |
| 6 | Regression System | 版本对比、Dataset 回放、Score Diff | Diff 报告标注回归项 |
| 7 | Plugin System | 外部插件生命周期管理 | 第三方可实现接口并注册 |
# AgentEval — 通用 AI Agent 对话评测平台 PRD

## 文档目录结构

```
docs/prd/
├── README.md                      # 本文件 — PRD 总览与索引
├── 00-tech-specification.md       # 统一技术规范（架构 / DTO / 错误码 / 日志 / 配置）
├── 01-domain-model.md             # 核心领域模型（字段级定义）
├── 02-core-foundation.md          # Phase 1 — Core Foundation 基础架构
├── 03-scenario-system.md          # Phase 2 — Scenario System 场景与数据集系统
├── 04-evaluation-engine.md        # Phase 3 — Evaluation Engine 执行引擎
├── 05-judge-system.md             # Phase 4 — Judge System 评分系统
├── 06-trace-report.md             # Phase 5 — Trace & Report 可观测系统
├── 07-regression-system.md        # Phase 6 — Regression System 版本对比
├── 08-plugin-system.md            # Phase 7 — Plugin System 插件系统
├── 09-scenario-dsl.md             # Scenario DSL 设计规范
└── 10-metrics-system.md           # 评测指标体系定义
```

## 阅读顺序

| 序号 | 文档 | 角色 | 依赖前置 |
|------|------|------|----------|
| 0 | `00-tech-specification.md` | 全局技术基线 | 无 |
| 1 | `01-domain-model.md` | 领域模型字典 | 00 |
| 2 | `09-scenario-dsl.md` | 场景 DSL 规范 | 00, 01 |
| 3 | `10-metrics-system.md` | 指标体系 | 00, 01 |
| 4 | `02-core-foundation.md` | Phase 1 实现 | 00, 01 |
| 5 | `03-scenario-system.md` | Phase 2 实现 | 00, 01, 02, 09 |
| 6 | `04-evaluation-engine.md` | Phase 3 实现 | 00, 01, 02, 03, 09 |
| 7 | `05-judge-system.md` | Phase 4 实现 | 00, 01, 03, 04, 10 |
| 8 | `06-trace-report.md` | Phase 5 实现 | 00, 01, 04, 05 |
| 9 | `07-regression-system.md` | Phase 6 实现 | 00, 01, 04, 05, 06 |
| 10 | `08-plugin-system.md` | Phase 7 实现 | 00, 01, 03, 04, 05, 06 |

## 技术选型（全局约束）

| 维度 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | AI 生态完善，类型注解支持好 |
| Web 框架 | FastAPI 0.110+ | 异步原生、自动 OpenAPI 文档、Pydantic v2 集成 |
| 数据库 | PostgreSQL 16 | JSONB 支持、GIN 索引、行级安全 |
| ORM | SQLAlchemy 2.0 (async) | 异步支持成熟、类型友好 |
| 缓存 | Redis 7 | 任务队列状态、分布式锁、Trace 缓冲 |
| 任务队列 | Celery 5.3 + Redis broker | 异步评测任务执行 |
| 对象存储 | MinIO / S3 兼容 | Dataset 文件、Report HTML、Trace dump |
| 前端 | React 18 + Vite + TypeScript | 组件生态丰富、类型安全 |
| 容器化 | Docker + Docker Compose | 开发环境一致 |

## Phase 概览

| Phase | 名称 | 核心交付物 | 验收里程碑 |
|-------|------|-----------|-----------|
| 1 | Core Foundation | 项目骨架、Workspace/Project CRUD、配置/日志/异常体系 | `GET /api/v1/health` 返回 200；Workspace CRUD 通过 |
| 2 | Scenario System | Dataset/Scenario CRUD、Scenario DSL 解析器 | DSL YAML 可解析为 Scenario 实体并持久化 |
| 3 | Evaluation Engine | Runner、Adapter SPI、并发执行、基础 Trace | 单个 Scenario 可端到端执行并产出 AgentExecution |
| 4 | Judge System | Rule/LLM/Embedding Judge、Score Aggregation | 对 AgentExecution 可产出多维 JudgeResult |
| 5 | Trace & Report | Trace Tree、Timeline、JSON/HTML Report | 可生成包含 Trace 树的可视化 HTML 报告 |
| 6 | Regression System | 版本对比、Dataset 回放、Score Diff | 两次评测可生成 Diff 报告并标注回归项 |
| 7 | Plugin System | Judge/Adapter/Dataset/Metrics/Report 插件 SPI | 第三方可实现接口并热加载 |
