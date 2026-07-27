# Architecture Overview

> **Depends on**: (无，本文档为顶层架构入口)
> **Referenced by**: ../README.md, ../architecture/design-principles.md, ../phases/phase-1-foundation.md

## 1. 定位

本文档是 AgentEval 系统的架构总览和文档体系导航入口。它定义了系统分层、核心数据流、子系统职责边界，并为整个文档体系提供阅读导航。

本文档只描述长期稳定的架构约束，不包含具体实现细节、代码示例或配置说明。

## 2. 系统分层

```
┌─────────────────────────────────────────────────┐
│                  API Layer (Controller)          │  FastAPI Router
│                  请求校验 / 路由 / 响应序列化      │
├─────────────────────────────────────────────────┤
│                 Application Layer (Service)      │  业务编排
│                 事务边界 / 领域调度 / 权限         │
├─────────────────────────────────────────────────┤
│                   Domain Layer                   │  纯领域逻辑
│           Entity / ValueObject / DomainEvent     │  不依赖框架
├─────────────────────────────────────────────────┤
│               Infrastructure Layer (Infra)       │  技术实现
│        DB / Cache / MQ / Storage / External API  │
└─────────────────────────────────────────────────┘
```

**依赖方向**：上层依赖下层，禁止反向依赖。Domain 层不依赖任何框架。

## 3. 核心数据流

```
用户创建 Evaluation
        │
        ▼
  EvaluationService ──→ 创建 Evaluation (status=pending)
        │                    │
        ▼                    ▼
  Runner Orchestrator    创建 ScenarioExecution 列表
        │
        ├──→ 对每个 Scenario:
        │       │
        │       ├──→ AdapterRegistry.create(config) → AgentAdapter
        │       │
        │       ├──→ AgentAdapter.execute(AgentRequest) → AgentResponse
        │       │       (Runner 通过包裹调用采集基础 Trace)
        │       │
        │       ├──→ 保存 AgentExecution + Conversation(JSONB) + Trace(JSONB)
        │       │
        │       └──→ 更新 ScenarioExecution (status=completed)
        │
        ├──→ 全部 Scenario 执行完成 → Evaluation (status=scoring)
        │
        ▼
  JudgeService ──→ 对每个 AgentExecution 执行评分
        │              │
        │              ├──→ RuleJudge / LLMJudge (通过 LLMClient)
        │              │
        │              └──→ ScoreAggregator 加权聚合 → JudgeResult + MetricScore
        │
        ▼
  ReportGenerator ──→ 生成 HTML / JSON 报告
        │                    │
        │                    ├──→ DerivedMetricProvider (按需计算衍生指标)
        │                    │
        │                    └──→ Jinja2 HTML 模板 / json.dumps
        │
        ▼
  Evaluation (status=completed)
```

## 4. 子系统职责边界

| 子系统 | 可读 | 可写 | 核心职责 |
|--------|------|------|----------|
| Workspace / Project | 全局 | 对应租户 | 多租户隔离、项目分组 |
| Dataset / Scenario | Project 内 | Project 内 | 场景数据管理、DSL 解析 |
| Evaluation Runner | Project 内 | Project 内 | 执行调度、Adapter 调用、Trace 采集 |
| Judge | Evaluation 内 | Evaluation 内 | 评分调度、指标计算 |
| Report | Evaluation 内 | 只读生成 | 报告渲染、衍生指标计算 |
| Regression | 跨 Evaluation | 只读分析 | 回归对比、差异分析 |
| Plugin | 全局 | 全局 | 外部插件发现/加载/配置 |

## 5. SPI 扩展点总览

| SPI 接口 | 契约文档 | 内置实现 | 外部可扩展 |
|----------|----------|----------|-----------|
| AgentAdapter | `../contracts/adapter-spi.md` | HTTP / OpenAI / Custom | ✅ |
| Judge | `../contracts/judge-spi.md` | Rule / LLM | ✅ |
| LLMClient | `../contracts/judge-spi.md` | OpenAI | ✅ |
| DSLParser | `../contracts/scenario-dsl.md` | YAML / JSON | ✅ |
| DerivedMetricProvider | `../phases/phase-5-report.md` | 内置衍生指标 | ✅ |

所有 SPI 遵循统一 Registry 模式（register / unregister / create / list），内置实现通过 Registry 静态注册，外部实现通过 Plugin 系统动态注册。

## 6. 文档体系导航

### 文档分层

| 层级 | 目录 | 定位 | 稳定性 |
|------|------|------|--------|
| Architecture | `architecture/` | 长期稳定的架构约束与设计原则 | 最高 |
| Contracts | `contracts/` | 跨 Phase 共享的接口契约与领域定义 | 高 |
| Tech Spec | `tech-spec.md` | 全局实现规范（API 格式/错误码/配置/日志） | 中 |
| Phases | `phases/` | 分阶段实现指南 | 随阶段演进 |
| Decisions | `decisions/` | 架构决策记录 (ADR) | 不可变 |

### 阅读路径

```
新成员入门:
  1. architecture/overview.md (本文档)
  2. architecture/design-principles.md
  3. contracts/domain-model.md
  4. tech-spec.md
  5. README.md (Phase 概览)

实现某个 Phase:
  1. phases/phase-N-*.md (目标 Phase)
  2. 相关 contracts/*.md (接口契约)
  3. architecture/design-principles.md (约束)
  4. tech-spec.md (实现规范)

理解某个决策:
  1. decisions/README.md (ADR 索引)
  2. decisions/NNNN-*.md (具体 ADR)
  3. 对应 contracts/ 或 phases/ 文档中的 ADR 引用
```

### 文档清单

```
docs/
├── README.md                              # 导航索引 + Phase 概览 + 技术选型
├── architecture/
│   ├── overview.md                        # ← 本文档
│   └── design-principles.md               # 设计原则
├── contracts/
│   ├── domain-model.md                    # 核心领域定义 + 状态机
│   ├── scenario-dsl.md                    # Scenario DSL 规范
│   ├── adapter-spi.md                     # Agent Adapter SPI 契约
│   ├── judge-spi.md                       # Judge SPI + LLMClient 契约
│   └── metrics-definition.md              # 评测指标体系
├── tech-spec.md                           # 全局实现规范
├── phases/
│   ├── phase-1-foundation.md              # Phase 1: 核心基础
│   ├── phase-2-scenario.md                # Phase 2: 场景系统
│   ├── phase-3-runner.md                  # Phase 3: 执行引擎
│   ├── phase-4-judge.md                   # Phase 4: 评分系统
│   ├── phase-5-report.md                  # Phase 5: Trace 与报告
│   ├── phase-6-regression.md              # Phase 6: 回归测试
│   └── phase-7-plugin.md                  # Phase 7: 插件系统
└── decisions/
    ├── README.md                          # ADR 模板 + 索引
    └── 0001-*.md ~ NNNN-*.md             # 架构决策记录
```

## 7. 技术选型概览

| 维度 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | 类型提示 + async/await + 生态丰富 |
| Web 框架 | FastAPI | 原生 async + OpenAPI 自动生成 + Pydantic 校验 |
| ORM | SQLAlchemy 2.0 (async) | 成熟 + async 支持 + 类型安全 |
| 数据库 | PostgreSQL 16 | JSONB + GIN 索引 + 行级安全 |
| 缓存 | Redis 7 | 任务队列 + 会话缓存 + 分布式锁 |
| 任务队列 | Celery 5.3 | 分布式执行 + 重试 + 定时任务 |
| 对象存储 | MinIO | S3 兼容 + 自托管 |
| 前端 | React 18 + Vite | 生态成熟 + HMR + 组件丰富 |
