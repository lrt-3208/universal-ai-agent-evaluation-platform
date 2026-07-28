# Route Map — 路由契约

> **Depends on**: `api-contract.md`
> **Referenced by**: 所有 `phases/*.md`

## 1. 路由表（唯一真相）

| 路由 | 页面组件 | Phase | 依赖 API | 守卫/重定向 |
|------|---------|-------|---------|------------|
| `/` | — | F1 | — | 重定向到 `/workspaces` |
| `/workspaces` | `WorkspaceListPage` | F1 | GET /workspaces | — |
| `/workspaces/:wsId/projects` | `ProjectListPage` | F1 | GET /workspaces/:id/projects | wsId 无效 → 404 页 |
| `/projects/:projId` | `ProjectOverviewPage` | F1 | GET /projects/:id | — |
| `/projects/:projId/datasets` | `DatasetListPage` | F2 | GET /projects/:id/datasets | — |
| `/datasets/:dsId/scenarios` | `ScenarioListPage` | F2 | GET /datasets/:id/scenarios | 分页参数入 searchParams |
| `/projects/:projId/evaluations` | `EvaluationListPage` | F3 | GET /projects/:id/evaluations | status 筛选入 searchParams |
| `/projects/:projId/evaluations/new` | `EvaluationCreatePage` | F3+F4 | POST evaluations, POST judge-configs/validate | 提交成功 → 详情页 |
| `/evaluations/:evalId` | `EvaluationDetailPage` | F3 | GET /evaluations/:id, /status, /executions | Tab 状态入 searchParams（?tab=） |
| `/evaluations/:evalId?tab=executions` | Tab: 执行列表 | F3/F4 | GET executions + judge-results | 默认 Tab |
| `/evaluations/:evalId?tab=trace` | Tab: Trace | F5 | GET executions/:id/trace, timeline | — |
| `/evaluations/:evalId?tab=reports` | Tab: 报告 | F5 | GET/POST reports | — |
| `/projects/:projId/regressions` | `RegressionListPage` | F6 | GET /projects/:id/regressions | — |
| `/projects/:projId/regressions/new` | `RegressionCreatePage` | F6 | POST regressions | 需选择 2 个 completed 评测 |
| `/regressions/:regId` | `RegressionDetailPage` | F6 | GET /regressions/:id, /report | — |
| `/plugins` | `PluginListPage` | F7 | GET /plugins | 全局级（不挂 project 下） |
| `*` | `NotFoundPage` | F1 | — | 404 兜底 |

## 2. 布局嵌套

```
<AppLayout>                    # 侧边栏 + 顶栏（全部路由共享）
  ├── 上下文选择器：顶栏 Workspace/Project 级联下拉（Zustand 持久化选中）
  ├── 侧边栏菜单（选中 project 后展开）：
  │     概览 / 数据集 / 评测 / 回归对比
  ├── 全局菜单：Workspaces / 插件管理
  └── <Outlet />               # 页面渲染出口
```

## 3. 路由规则（MUST）

- 所有列表页的分页/筛选/Tab 状态存 URL searchParams（刷新不丢失）
- 面包屑从路由层级自动生成：Workspace 名 / Project 名 / 页面名（名称从 React Query 缓存取）
- 路由按 Phase 功能域 lazy loading：`pages/evaluation/` 等目录级 `React.lazy`
- 深链接可用：直接访问 `/evaluations/:id` 必须能完整渲染（不依赖前置页面注入的内存态）
