# Phase F3: Evaluation（评测创建与执行监控）

> **Depends on**: `phase-f1-foundation.md`, `phase-f2-dataset-scenario.md`, `../contracts/ui-domain-model.md`
> **Referenced by**: `phase-f4-judge.md`, `phase-f5-trace-report.md`, `phase-f6-regression.md`

## 1. 目标

实现评测的创建向导、列表、详情与**实时执行监控**（轮询）。这是平台核心操作流，交互质量优先级最高。

## 2. 页面设计

### 2.1 EvaluationCreatePage（`/projects/:projId/evaluations/new`）— 分步向导

```
Step 1 基本信息: name、version_label、选择 Dataset（下拉，显示场景数）
Step 2 Agent 配置: 默认继承 Project.agent_config，可覆盖（adapter_type + endpoint）
Step 3 Judge 配置: （F4 实现，F3 阶段仅放置默认 rule judge 配置）
Step 4 确认提交: 汇总预览 → POST → 跳转详情页
```

### 2.2 EvaluationListPage（`/projects/:projId/evaluations`）

- 表格：name、version_label、status（StatusTag，running 用 processing 动态样式）、创建时间。**列表行不展示精确进度/pass_rate**（后端列表响应不含此数据，禁止 N+1 逐行拉 /status，见 api-contract §1.4）
- status 筛选 Tab（all/running/completed/failed）入 searchParams
- **列表级轮询**：存在 running 项时整表 5s 轮询，否则不轮询
- 行操作：查看、取消（仅 pending/running）

### 2.3 EvaluationDetailPage（`/evaluations/:evalId`）

- 头部：状态、进度环（done/total）、耗时、操作（取消/发起评分/生成报告）
- 状态轮询：`useEvaluationStatus(id)` — running 2s 轮询，终态停止并 invalidate executions
- Tab: executions（默认）| trace（F5）| reports（F5）
- executions Tab：表格（scenarioTitle、status、overallScore、verdict、latency），行点击抽屉展示**对话内容**（MessageVM 气泡样式，user 右/assistant 左，monospace 代码字体）

## 3. 核心 Hook 契约

```typescript
// hooks/useEvaluationStatus.ts — 本 Phase 最重要的抽象
useEvaluationStatus(evalId): {
  status, counts, isPolling
}
// 实现: useQuery({
//   queryKey: ['evaluation-status', evalId],
//   refetchInterval: (q) => TERMINAL.has(q.state.data?.status) ? false : 2000,
//   refetchIntervalInBackground: false,
// })
// 终态迁移时: invalidateQueries(['executions', evalId]) + ['evaluations']
```

## 4. Task 分解

### Task F3.1: 创建向导（Step 1/2/4，Step 3 留桩）
- **AC**: 提交成功跳转详情页

### Task F3.2: 评测列表 + 筛选 + 列表级轮询
- **AC**: running 时自动刷新，完成后停止

### Task F3.3: 详情页 + 状态轮询 Hook
- **Dependencies**: F3.2
- **AC**: 状态终态自动停止轮询

### Task F3.4: 执行列表 + 对话查看抽屉
- **Dependencies**: F3.3
- **AC**: 对话气泡正确渲染 user/assistant

## 5. 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|---------|
| AC-F3-01 | 向导完整走通并创建评测，跳转详情页 | E2E |
| AC-F3-02 | 详情页 running 期间进度自动增长（无手动刷新） | E2E |
| AC-F3-03 | 评测完成后轮询停止（网络面板无持续请求） | E2E |
| AC-F3-04 | 执行列表展示每个场景的 status 和 score | E2E |
| AC-F3-05 | 点击执行行，抽屉展示完整对话内容 | E2E |
| AC-F3-06 | 取消 running 评测后状态变为 cancelled | E2E |
| AC-F3-07 | 列表 status 筛选正确且入 URL | E2E |
| AC-F3-08 | Dataset 无场景时创建评测，400 错误正确提示 | E2E |
| AC-F3-09 | EvaluationDetailVM 进度计算正确（单测：total=0、部分完成、全完成） | Vitest |
