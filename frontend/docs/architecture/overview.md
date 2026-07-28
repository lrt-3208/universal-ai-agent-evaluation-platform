# Frontend Architecture Overview — 前端架构概览

> **Depends on**: 无（阅读起点）
> **Referenced by**: 所有其他文档

## 1. 系统定位

AgentEval 前端是纯后端评测平台的**管理控制台**（内部中后台工具），覆盖评测全生命周期的可视化操作：

```
Workspace → Project → Dataset → Scenario → Evaluation → Judge → Report → Regression → Plugin
```

后端 60 个 REST 端点是前端的唯一数据源（见 `contracts/api-contract.md`）。

## 2. 分层架构

```
┌──────────────────────────────────────────────┐
│                  Pages 层                     │
│   页面组件：组装布局 + 业务组件 + 数据 hooks    │
├──────────────────────────────────────────────┤
│               Components 层                   │
│   通用组件（StatusTag/ScoreBadge/图表封装）    │
│   仅接收 props，不直接访问 API                 │
├──────────────────────────────────────────────┤
│                 Hooks 层                      │
│   React Query hooks：useEvaluations 等        │
│   封装 queryKey + 轮询 + 失效策略              │
├──────────────────────────────────────────────┤
│                  API 层                       │
│   Axios client + 生成类型 + endpoint 函数     │
│   唯一的后端访问点                             │
├──────────────────────────────────────────────┤
│              Backend REST API                 │
│   http://localhost:9000/api/v1/*             │
└──────────────────────────────────────────────┘
```

**依赖方向严格向下**：Pages → Components/Hooks → API。禁止反向依赖、禁止跨层调用（Page 不直接 import axios）。

## 3. 页面地图

```
AppLayout（侧边栏 + 顶栏 + 面包屑）
├── /workspaces                      Workspace 列表（F1）
├── /workspaces/:wsId/projects       Project 列表（F1）
├── /projects/:projId                Project 概览（F1）
│   ├── /datasets                    Dataset 列表（F2）
│   │   └── /:dsId/scenarios         Scenario 列表 + 批量导入（F2）
│   ├── /evaluations                 Evaluation 列表（F3）
│   │   ├── /new                     评测创建向导（F3 + F4 judge 配置步骤）
│   │   └── /:evalId                 评测详情（F3）
│   │       ├── executions Tab       场景执行列表 + 评分（F3/F4）
│   │       ├── trace Tab            Trace 时间线（F5）
│   │       └── reports Tab          报告列表/预览（F5）
│   └── /regressions                 回归对比列表（F6）
│       ├── /new                     创建对比（F6）
│       └── /:regId                  Diff 详情页（F6）
└── /plugins                         插件管理（F7，全局级）
```

## 4. 关键数据流

### 4.1 评测执行监控（核心流程）

```
用户创建评测（POST /projects/{id}/evaluations）
  → 后端 202 返回 evaluation_id（后台异步执行）
  → 前端 useQuery(['evaluation-status', id])
      refetchInterval: status ∈ {pending, running} ? 2000 : false
  → 状态终态（completed/failed）→ 停止轮询 → invalidate executions 列表
```

### 4.2 报告生成

```
POST /evaluations/{id}/reports → 202（generating）
  → 轮询 GET /reports/{id} 至 status=completed
  → 预览：iframe 加载 GET /reports/{id}/preview
  → 下载：window.open GET /reports/{id}/download
```

## 5. 与后端 Phase 的映射

| 前端 Phase | 后端依赖 Phase | 依赖的后端端点组 |
|-----------|--------------|----------------|
| F1 | Phase 1 | workspaces, projects, health |
| F2 | Phase 2 | datasets, scenarios |
| F3 | Phase 3 | evaluations, executions, status |
| F4 | Phase 4 | judge-configs/validate, judge-results |
| F5 | Phase 5 | traces, timeline, reports |
| F6 | Phase 6 | regressions, replay |
| F7 | Phase 7 | plugins |
