# AgentEval Frontend — 评测平台前端

> **Depends on**: 后端 `../../docs/`（API 唯一真相），本文档体系与后端四层结构完全对齐。

## 文档目录结构（四层）

```
frontend/docs/
├── README.md                              # 本文件 — 导航入口
├── tech-spec.md                           # 全局实现规范（目录结构、命名、状态管理、请求层）
│
├── architecture/                          # 架构原则（长期稳定）
│   ├── overview.md                        # 前端架构概览 + 页面地图
│   └── design-principles.md               # 前端设计原则与约束
│
├── contracts/                             # 契约（前端所有实现的唯一真相）
│   ├── api-contract.md                    # 后端 API 契约（60 端点清单 + 类型生成规则）
│   ├── route-map.md                       # 路由契约（URL ↔ 页面 ↔ API 映射）
│   ├── ui-domain-model.md                 # 前端视图模型（API → 视图转换规则）
│   ├── design-tokens.md                   # 设计令牌（色彩/间距/字体，主题唯一真相）
│   └── error-handling.md                  # 错误处理契约（后端错误码 → 用户提示映射）
│
├── phases/                                # 实现指南（每个 Phase 包含 Task 分解）
│   ├── phase-f1-foundation.md             # F1: 脚手架 + 布局 + Workspace/Project
│   ├── phase-f2-dataset-scenario.md       # F2: 数据集 + 场景管理
│   ├── phase-f3-evaluation.md             # F3: 评测创建 + 执行监控
│   ├── phase-f4-judge.md                  # F4: Judge 配置 + 评分展示
│   ├── phase-f5-trace-report.md           # F5: Trace 可视化 + 报告
│   ├── phase-f6-regression.md             # F6: 回归对比
│   └── phase-f7-plugin.md                 # F7: 插件管理
│
└── decisions/                             # ADR（架构决策记录，不可变）
    ├── README.md                          # ADR 索引 + 规则
    ├── 0001-react-vite-stack.md           # 框架选型
    ├── 0002-state-management.md           # 状态管理方案
    └── 0003-api-client-codegen.md         # API 类型生成策略
```

## 阅读路径

| 序号 | 文档 | 角色 | 依赖前置 |
|------|------|------|----------|
| 0 | `architecture/overview.md` | 架构全景 + 页面地图 | 无 |
| 1 | `architecture/design-principles.md` | 设计约束 | 0 |
| 2 | `tech-spec.md` | 全局实现规范 | 0, 1 |
| 3 | `contracts/api-contract.md` | API 契约（唯一真相） | 2 |
| 4 | `contracts/route-map.md` | 路由契约 | 3 |
| 5 | `contracts/ui-domain-model.md` | 视图模型 | 3 |
| 6 | `contracts/design-tokens.md` | 设计令牌 | 1 |
| 7 | `contracts/error-handling.md` | 错误处理契约 | 3 |
| 8 | `phases/phase-f1-foundation.md` | F1 实现 | 2, 3, 4, 6 |
| 9 | `phases/phase-f2-dataset-scenario.md` | F2 实现 | 3, 5, 8 |
| 10 | `phases/phase-f3-evaluation.md` | F3 实现 | 3, 5, 8, 9 |
| 11 | `phases/phase-f4-judge.md` | F4 实现 | 3, 5, 10 |
| 12 | `phases/phase-f5-trace-report.md` | F5 实现 | 3, 5, 10, 11 |
| 13 | `phases/phase-f6-regression.md` | F6 实现 | 10, 11, 12 |
| 14 | `phases/phase-f7-plugin.md` | F7 实现 | 3, 8 |

## 技术选型（全局约束）

| 维度 | 选型 | 理由 |
|------|------|------|
| 框架 | React 18 + TypeScript 5 | 组件生态丰富、类型安全 |
| 构建 | Vite 5 | 快速冷启动、HMR |
| 路由 | React Router v6 | 声明式路由、嵌套布局 |
| 服务端状态 | TanStack Query v5 | 缓存/轮询/失效管理，天然适配评测状态轮询 |
| 客户端状态 | Zustand | 轻量、无样板代码 |
| UI 组件库 | Ant Design 5 | 中后台组件全（表格/表单/树），设计令牌可定制 |
| 图表 | ECharts 5 | 雷达图/时间线/直方图全覆盖 |
| API 类型 | openapi-typescript | 从后端 `/openapi.json` 自动生成，字段永不漂移 |
| HTTP | Axios | 拦截器统一处理 ApiResponse 信封与错误 |
| 测试 | Vitest + Playwright | 单测 + E2E（打真实后端） |

## Phase 概览

| Phase | 名称 | 核心交付物 | 验收里程碑 |
|-------|------|-----------|----------|
| F1 | Foundation | 脚手架、布局、API Client、Workspace/Project 页 | 页面可创建 Workspace 并列表展示 |
| F2 | Dataset & Scenario | 数据集/场景 CRUD、批量导入 | 可通过 UI 导入场景并查看列表 |
| F3 | Evaluation | 评测创建向导、状态轮询、进度展示 | UI 发起评测并实时看到完成状态 |
| F4 | Judge & Score | Judge 配置表单、评分结果展示 | 评分明细在 UI 可见 |
| F5 | Trace & Report | Trace 时间线、报告预览/下载 | 报告在 UI 内预览 |
| F6 | Regression | 版本对比页、Diff 高亮 | 两次评测对比结果可视化 |
| F7 | Plugin | 插件列表、启停、配置 | UI 可启用/禁用插件 |

## 开发流程（与后端对齐）

```
Contract Freeze（契约冻结）
  → 逐 Phase 实现（F1 → F7）
  → 每 Phase 验收测试（组件测试 + Playwright E2E）
  → 每 Phase 结束回归前序 Phase
  → 最终全链路 E2E（对齐后端 test_e2e_llm.py 场景）
```

## 全链路 E2E 验收（F7 完成后执行，e2e/full-pipeline.spec.ts）

| 编号 | 验收项 |
|------|--------|
| AC-E2E-01 | UI 完整走通：建 Workspace → Project → Dataset → 批量场景 → 创建评测（rule+llm Judge） |
| AC-E2E-02 | 评测执行完成，执行列表展示评分与 verdict |
| AC-E2E-03 | 生成 HTML 报告并在 UI 预览 |
| AC-E2E-04 | 基于两次评测创建回归分析，Diff 页正确展示 |
| AC-E2E-05 | 全程无 console error（Playwright 监听 page error） |
