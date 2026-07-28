# API Contract — 后端 API 契约（前端唯一数据源）

> **Depends on**: `../tech-spec.md`，后端 `/openapi.json`（运行时真相）
> **Referenced by**: `route-map.md`, `ui-domain-model.md`, 所有 `phases/*.md`
> **同步规则**: 本文档是端点清单快照；字段级类型以 `npm run gen:api` 生成的 `src/api/generated/schema.d.ts` 为准。后端 API 变更 → 重新生成 → 本文档同步更新。

## 1. 通用约定

### 1.1 Base URL 与信封

- Base: `${VITE_API_BASE_URL}/api/v1`（开发经 Vite proxy）
- 所有响应信封：`{ code: number, message: string, data: T, request_id: string | null }`
  - 成功判定：**`code === 0`**（已实测；message 可能是 "ok" 或 "success"，不可依赖）
  - `request_id` 可能为 null，错误提示时需做空值兼容
- 分页列表响应 data 结构：`{ items: T[], total: number, page: number, page_size: number, total_pages: number }`
- **例外**：`GET /evaluations/{id}/executions` 返回**非分页纯数组**（已实测）；`GET /health` 不带信封；`POST /evaluations/{id}/replay` 返回**无信封裸对象** `{evaluation_id, message}`（已实测）；**regressions 全部端点无信封**（POST/GET 详情返回裸对象、列表返回裸数组，已实测）

### 1.2 关键字段约束（前端表单校验必须对齐）

| 字段 | 约束 | 出处 |
|------|------|------|
| Workspace.slug / Project.slug | `^[a-z0-9-]+$` | 后端 schema 校验 |
| Dataset.version | semver `^\d+\.\d+\.\d+$` | 后端 schema 校验 |
| Scenario.input | 对象且用户消息键名必须是 **`user_message`**（Runner 读 `input_data["user_message"]`，用 `query` 等键名会导致 Agent 收到空输入 — 已实测踩坑），字段名是 `input` 非 `input_data` | 后端 Runner `_build_messages` |
| Project.agent_config | 必填，含 `adapter_type` + `endpoint` | 后端 project schema |
| agent_config.endpoint | 填 Agent base URL，**不带 /chat**（HTTP Adapter 自动拼接） | 后端 HTTP Adapter 行为 |

### 1.3 异步语义（前端必须轮询的端点）

| 操作 | 创建响应 | 轮询端点 | 终态 |
|------|---------|---------|------|
| 创建评测 | 201/202 | `GET /evaluations/{id}/status` | completed / failed / cancelled |
| 生成报告 | 202 | `GET /reports/{id}` | completed / failed |
| Dataset Replay | 202 | `GET /evaluations/{newId}/status` | completed / failed |

### 1.4 列表行字段边界（已实测，前端设计必须遵守）

- Evaluation 列表行**不包含** pass_rate / 进度计数，只有 status；进度与 pass_rate 只能从 `GET /evaluations/{id}/status` 与 executions 聚合获得
- 因此：列表页禁止逐行调 /status（N+1），详情页才展示精确进度（见 ui-domain-model §2.1）
- Timeline 端点 data 已含算好的 `events[]`（span_id/name/span_type/start_ms/duration_ms/depth/status/label）与 `total_duration_ms`，前端无需自行计算 offset/depth

### 1.5 类型生成覆盖缺口（已实测）

部分后端端点未声明 `response_model`，OpenAPI 中响应 schema 为空，生成类型为 `unknown`：

| 端点组 | 状态 | 处理方式 |
|---------|------|---------|
| workspaces、projects 全部 | 无 response schema | 在 `src/api/types.ts` 手写**实测结构**类型，文件头注明“待后端补 response_model 后改为生成类型” |
| evaluations、reports、plugins、traces、judge 等 | 有 response schema | 直接用生成类型 |

**实测结构**：
- Workspace 列表项：`{ id, name, slug, project_count }`
- Project 列表项：含 `id, name, slug, workspace_id, agent_config` 等

> 后端后续补全 response_model 后，重跑 `gen:api` 并将手写类型切换为生成类型（手写区域需保持最小）。

## 2. 端点清单（60 个，按前端 Phase 分组）

### F1 — Workspace / Project / Health

| Method | Path | 用途 |
|--------|------|------|
| GET | `/health` | 健康检查（启动页系统状态） |
| POST | `/workspaces` | 创建 Workspace |
| GET | `/workspaces` | Workspace 列表 |
| GET | `/workspaces/{workspace_id}` | Workspace 详情 |
| PUT | `/workspaces/{workspace_id}` | 更新 |
| DELETE | `/workspaces/{workspace_id}` | 删除（软删） |
| POST | `/workspaces/{workspace_id}/projects` | 创建 Project |
| GET | `/workspaces/{workspace_id}/projects` | Project 列表 |
| GET | `/projects/{project_id}` | Project 详情 |
| PUT | `/projects/{project_id}` | 更新 |
| DELETE | `/projects/{project_id}` | 删除 |

### F2 — Dataset / Scenario

| Method | Path | 用途 |
|--------|------|------|
| POST | `/projects/{project_id}/datasets` | 创建 Dataset |
| GET | `/projects/{project_id}/datasets` | Dataset 列表 |
| GET | `/datasets/{dataset_id}` | 详情 |
| PUT | `/datasets/{dataset_id}` | 更新 |
| DELETE | `/datasets/{dataset_id}` | 删除 |
| GET | `/datasets/{dataset_id}/export` | 导出 DSL |
| POST | `/projects/{project_id}/datasets/import` | DSL 导入 |
| POST | `/projects/{project_id}/datasets/import/validate` | 导入前校验 |
| POST | `/datasets/{dataset_id}/scenarios` | 创建单个场景 |
| GET | `/datasets/{dataset_id}/scenarios` | 场景列表（分页） |
| POST | `/datasets/{dataset_id}/scenarios/batch` | 批量创建场景 |
| GET | `/scenarios/{scenario_id}` | 场景详情 |
| PUT | `/scenarios/{scenario_id}` | 更新 |
| DELETE | `/scenarios/{scenario_id}` | 删除 |

### F3 — Evaluation / Execution

| Method | Path | 用途 |
|--------|------|------|
| POST | `/projects/{project_id}/evaluations` | 创建评测（异步触发执行） |
| GET | `/projects/{project_id}/evaluations` | 评测列表（支持 status 筛选） |
| GET | `/evaluations/{evaluation_id}` | 详情 |
| GET | `/evaluations/{evaluation_id}/status` | 状态 + 执行计数（**轮询端点**） |
| POST | `/evaluations/{evaluation_id}/cancel` | 取消 |
| GET | `/evaluations/{evaluation_id}/executions` | 场景执行列表（**返回纯数组，无分页**） |
| GET | `/evaluations/{evaluation_id}/executions/{exec_id}` | 执行详情（含对话） |

### F4 — Judge

| Method | Path | 用途 |
|--------|------|------|
| POST | `/projects/{project_id}/judge-configs/validate` | Judge 配置校验（向导步骤实时校验） |
| POST | `/evaluations/{evaluation_id}/judge` | 手动触发评分 |
| GET | `/scenario-executions/{exec_id}/judge-results` | 单执行的评分结果 |
| GET | `/judge-results/{result_id}` | 评分结果详情 |

### F5 — Trace / Report

| Method | Path | 用途 |
|--------|------|------|
| GET | `/traces/{trace_id}` | Trace 树 |
| GET | `/traces/{trace_id}/spans` | Span 列表 |
| GET | `/traces/{trace_id}/timeline` | 时间线数据（可视化直接消费） |
| GET | `/evaluations/{evaluation_id}/executions/{exec_id}/trace` | 按执行查 Trace |
| GET | `/agent-executions/{exec_id}/trace` | 按 AgentExecution 查 Trace |
| POST | `/evaluations/{evaluation_id}/reports` | 生成报告（202 异步） |
| GET | `/evaluations/{evaluation_id}/reports` | 报告列表 |
| GET | `/reports/{report_id}` | 报告详情（轮询 status） |
| GET | `/reports/{report_id}/download` | 下载（Content-Disposition） |
| GET | `/reports/{report_id}/preview` | 预览（iframe src） |

### F6 — Regression

| Method | Path | 用途 |
|--------|------|------|
| POST | `/projects/{project_id}/regressions` | 创建回归分析（同步返回结果） |
| GET | `/projects/{project_id}/regressions` | 列表 |
| GET | `/regressions/{regression_id}` | 详情（含 scenario_diffs） |
| GET | `/regressions/{regression_id}/report` | Diff 报告（html/json，query: format） |
| POST | `/evaluations/{evaluation_id}/replay` | Dataset 回放（新 agent_config） |

### F7 — Plugin

| Method | Path | 用途 |
|--------|------|------|
| GET | `/plugins` | 插件列表（query: type） |
| POST | `/plugins/discover` | 重新扫描插件目录 |
| GET | `/plugins/types/{plugin_type}` | 按类型筛选 |
| GET | `/plugins/{plugin_name}` | 详情 |
| POST | `/plugins/{plugin_name}/enable` | 启用 |
| POST | `/plugins/{plugin_name}/disable` | 禁用 |
| POST | `/plugins/{plugin_name}/reload` | 重载 |
| PUT | `/plugins/{plugin_name}/config` | 更新配置 |

## 3. 核心枚举（前端 StatusTag 映射表数据源）

| 枚举 | 值 | 使用位置 |
|------|-----|---------|
| Evaluation.status | pending / running / completed / failed / cancelled | 评测列表、详情 |
| ScenarioExecution.status | pending / running / completed / failed / timeout / skipped | 执行列表 |
| overall_verdict | pass / partial / fail | 评分展示 |
| Report.status | generating / completed / failed | 报告列表 |
| Regression verdict | improved / regressed / unchanged / flaky | Diff 表格 |
| regression_risk | low / medium / high / critical | 回归摘要 |
| Plugin.status | enabled / disabled / error | 插件列表 |
| judge_type | rule / llm（+ 插件动态扩展） | Judge 配置、结果展示 |
