# Phase F5: Trace & Report（Trace 可视化与报告）

> **Depends on**: `phase-f3-evaluation.md`, `phase-f4-judge.md`, `../contracts/ui-domain-model.md`
> **Referenced by**: `phase-f6-regression.md`

## 1. 目标

实现评测详情的 trace Tab（时间线可视化）与 reports Tab（生成/轮询/预览/下载）。

## 2. 页面设计

### 2.1 trace Tab

- 左侧：执行选择列表（复用 executions 数据）
- 右侧：选中执行的 Trace 视图，两种模式切换：
  - **时间线模式**（默认）：ECharts custom series 甘特图 — X 轴相对时间(ms)，Y 轴按 depth 泳道；span 颜色按 kind（colorTraceLLM/Tool/Other 令牌）；hover 展示 name/duration/status；error span 红色描边
  - **树模式**：antd Tree 展示 span 层级，节点显示 name + duration
- 数据源：`GET /evaluations/{id}/executions/{execId}/trace` + `GET /traces/{traceId}/timeline`
- 无 Trace 时展示 EmptyState（"该执行未产生 Trace"）

### 2.2 reports Tab

```
[生成 HTML 报告] [生成 JSON 报告] 按钮
  → POST reports（202）→ 列表新增 generating 行（轮询该 report 2s）
  → completed：行操作 [预览] [下载]
预览：Modal 内 iframe src = /api/v1/reports/{id}/preview
下载：window.open(/api/v1/reports/{id}/download)
```

- 报告列表：format、status、created_at、summary 摘要（pass_rate 等）
- failed 状态展示 error tooltip

## 3. 关键实现约束

- TimelineItemVM 仅做字段映射（后端 events 已含 start_ms/duration_ms/depth，见 api-contract §1.4），映射函数单测覆盖（空 events、含 error span、多层 depth）
- ECharts 实例在 Tab 切换时 dispose，防泄漏
- iframe 预览用后端同源代理路径（经 Vite proxy），避免 CSP 问题

## 4. Task 分解

### Task F5.1: Timeline 数据转换 + 甘特图组件
- **AC**: 嵌套 span 正确分泳道渲染

### Task F5.2: Trace 树模式 + 模式切换
- **Dependencies**: F5.1
- **AC**: 两种模式数据一致

### Task F5.3: 报告生成 + 轮询 + 预览/下载
- **AC**: 见验收标准

## 5. 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|---------|
| AC-F5-01 | 时间线展示 span 且颜色按 kind 区分 | E2E |
| AC-F5-02 | hover span 展示名称与耗时 | E2E |
| AC-F5-03 | 树模式展示 span 层级 | E2E |
| AC-F5-04 | 生成报告后行内状态从 generating 自动变 completed | E2E |
| AC-F5-05 | 预览 Modal 内正确渲染 HTML 报告 | E2E |
| AC-F5-06 | 下载触发文件保存 | E2E |
| AC-F5-07 | TimelineVM 字段映射正确（空 events / error span / 多层 depth 三组用例） | Vitest |
| AC-F5-08 | 无 Trace 的执行展示 EmptyState 不报错 | E2E |
