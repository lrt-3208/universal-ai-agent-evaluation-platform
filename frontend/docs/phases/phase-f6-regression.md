# Phase F6: Regression（版本回归对比）

> **Depends on**: `phase-f3-evaluation.md`, `phase-f4-judge.md`, `phase-f5-trace-report.md`, `../contracts/ui-domain-model.md`
> **Referenced by**: 无

## 1. 目标

实现回归分析的创建、Diff 结果可视化（场景级 + 指标级）、Dataset 回放入口。

## 2. 页面设计

### 2.1 RegressionCreatePage（`/projects/:projId/regressions/new`）

- 表单：name、baseline 评测选择、target 评测选择（两个下拉均只列 completed 评测，展示 version_label + dataset 名）
- 前端预校验：baseline 与 target 的 dataset_id 不一致时禁用提交并提示（后端 409 兜底）
- 可选参数：regression_threshold（默认 0.05，滑块 0~1）
- 提交后**同步返回**结果 → 跳转详情页

### 2.2 RegressionDetailPage（`/regressions/:regId`）

```
┌ 摘要区 ─────────────────────────────────────┐
│ overall_verdict 大标签 + regression_risk 色阶  │
│ 统计卡: total/improved/regressed/unchanged/flaky│
├ 指标级 Diff ─────────────────────────────────┤
│ 表格: metric_key | baseline_mean | target_mean │
│       | delta(色阶) | direction | 受影响场景数   │
├ 场景级 Diff ─────────────────────────────────┤
│ 表格(ScenarioDiffVM): 场景 | baseline | target  │
│   | delta | verdict Tag                        │
│ verdict 筛选; regressed 行红色底纹置顶          │
│ 展开行: metricDeltas 明细（动态指标）            │
├ 操作 ───────────────────────────────────────┤
│ [查看 HTML Diff 报告](iframe Modal)             │
│ [Dataset 回放] → 弹窗输入新 agent_config        │
│   → POST replay → 跳转新评测详情页               │
└─────────────────────────────────────────────┘
```

### 2.3 RegressionListPage

- 表格：name、baseline/target 名、overall_verdict、regression_risk、创建时间

## 3. Task 分解

### Task F6.1: 创建页 + Dataset 一致性预校验
- **AC**: dataset 不一致时前端拦截

### Task F6.2: 详情页（摘要 + 双层 Diff 表格）
- **AC**: regressed 行高亮置顶，展开行显示指标明细

### Task F6.3: Diff 报告预览 + Replay 流程
- **Dependencies**: F6.2
- **AC**: replay 后跳转新评测并开始轮询

## 4. 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|---------|
| AC-F6-01 | 创建回归分析成功并跳转详情页 | E2E |
| AC-F6-02 | 选择不同 dataset 的两评测时提交被前端拦截 | E2E |
| AC-F6-03 | 摘要区统计数与后端 summary 一致 | E2E |
| AC-F6-04 | 场景 Diff 表 delta 色阶正确（负红正绿） | E2E |
| AC-F6-05 | 展开行展示动态 metricDeltas | E2E |
| AC-F6-06 | verdict 筛选正确 | E2E |
| AC-F6-07 | HTML Diff 报告可预览 | E2E |
| AC-F6-08 | Replay 弹窗提交后跳转新评测详情 | E2E |
