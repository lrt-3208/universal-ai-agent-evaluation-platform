# Phase F4: Judge & Score（Judge 配置与评分展示）

> **Depends on**: `phase-f3-evaluation.md`, `../contracts/ui-domain-model.md`
> **Referenced by**: `phase-f5-trace-report.md`, `phase-f6-regression.md`

## 1. 目标

补全评测向导的 Judge 配置步骤（Step 3），实现评分结果的完整展示（多 Judge、动态指标集）。

## 2. 页面设计

### 2.1 Judge 配置步骤（向导 Step 3）

- 可添加多个 Judge 配置卡片，每张卡片：
  - judge_type 下拉：rule / llm（选项动态来自后端能力，插件 Judge 在 F7 后自动出现）
  - rule：metrics 多选（correctness/forbidden_check/tool_accuracy/intent_match）
  - llm：metrics 多选（correctness/hallucination/coherence/planning_score/memory_accuracy）+ 可选 model/temperature 参数
  - weights：每个选中 metric 的权重输入（默认 1.0）
- 提交前调用 `POST /projects/{id}/judge-configs/validate` 实时校验，错误内联展示
- 无 LLM Judge 时提示"LLM 评分依赖后端 .env 配置"

### 2.2 评分展示（执行详情抽屉扩展）

- 抽屉内新增"评分"区域：`GET /scenario-executions/{id}/judge-results`
- 按 judgeType 分组的 `JudgeResultCard`：
  - 头部：judge_type 标签 + overall_score（ScoreBadge 色阶）+ verdict
  - 内容：MetricScoreVM 列表（metricKey、score 进度条、reasoning 折叠展示）
  - **动态渲染任意 metric_key**（开闭原则，禁止硬编码指标枚举）
- 评测详情头部：pass_rate 汇总 + "发起评分"按钮（`POST /evaluations/{id}/judge`，用于补评）

### 2.3 指标雷达图

- 详情页概览区：ECharts 雷达图展示评测级各指标均值
- **数据源（避免 N+1）**：优先取已完成报告的 `metrics_snapshot`（`GET /evaluations/{id}/reports` 取最新 completed）；无报告时雷达图区域展示引导："生成报告后查看指标分布"（禁止逐 execution 拉 judge-results 聚合）
- 指标轴动态生成（有几个 metric_key 画几根轴）

## 3. Task 分解

### Task F4.1: Judge 配置表单 + validate 集成
- **AC**: 非法配置提交前被 validate 拦截并内联展示

### Task F4.2: JudgeResultCard + MetricScore 展示
- **AC**: rule 和 llm 结果同时正确展示

### Task F4.3: 指标雷达图 + pass_rate 汇总
- **Dependencies**: F4.2
- **AC**: 指标轴随数据动态变化

## 4. 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|---------|
| AC-F4-01 | 向导可配置 rule + llm 双 Judge 并创建评测 | E2E |
| AC-F4-02 | 未知 judge_type 被 validate 拦截展示错误 | E2E |
| AC-F4-03 | 执行抽屉展示按 Judge 分组的评分卡 | E2E |
| AC-F4-04 | metric reasoning 可展开查看 | E2E |
| AC-F4-05 | ScoreBadge 色阶正确（≥0.8 绿 / ≥0.5 金 / <0.5 红） | Vitest |
| AC-F4-06 | 雷达图指标轴 = 报告 metrics_snapshot 的 metric_key 集合；无报告时展示引导而非空图 | E2E |
| AC-F4-07 | 手动"发起评分"后评分区自动刷新 | E2E |
| AC-F4-08 | 新增未知 metric_key 数据时 UI 正常渲染（不崩溃/不丢弃） | Vitest |
