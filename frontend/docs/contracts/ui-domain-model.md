# UI Domain Model — 前端视图模型契约

> **Depends on**: `api-contract.md`
> **Referenced by**: `phases/phase-f2` ~ `phase-f6`

## 1. 原则

- API 类型（generated）描述后端返回；视图模型描述页面需要
- 转换函数命名 `toXxxVM(apiData)`，集中在 `src/types/`，必须有单测
- 只有当"页面需要的形状 ≠ API 形状"时才建视图模型，简单透传不建

## 2. 视图模型定义

### 2.1 EvaluationListItemVM / EvaluationDetailVM（评测列表/详情）

```typescript
// 列表行：后端列表响应不含进度/pass_rate（api-contract §1.4），禁止 N+1 逐行拉 status
interface EvaluationListItemVM {
  id: string;
  name: string;
  status: EvaluationStatus;          // 列表只展示 StatusTag，running 时用动态 processing 样式代替精确进度条
  versionLabel: string | null;
  datasetId: string;
  createdAt: string;
}

// 详情头部：由详情 + /status 两个查询组合
interface EvaluationDetailVM extends EvaluationListItemVM {
  progress: {                        // 仅详情页，来自 GET /evaluations/{id}/status
    total: number;                   // total_scenarios
    done: number;                    // completed + failed + timeout + skipped
    percent: number;                 // done / total * 100，total=0 时为 0
  };
  passRate: number | null;           // 从 executions（纯数组）聚合 verdict=pass 占比，无评分时 null
}
```

### 2.2 ExecutionVM（场景执行行）

```typescript
interface ExecutionVM {
  id: string;
  scenarioTitle: string;
  status: ExecutionStatus;
  overallScore: number | null;       // 0~1
  overallVerdict: 'pass' | 'partial' | 'fail' | null;
  latencyMs: number | null;
  conversation: MessageVM[];         // 从 conversation_data.messages 提取
}

interface MessageVM {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
}
```

### 2.3 MetricScoreVM（评分明细，动态指标集）

```typescript
interface MetricScoreVM {
  metricKey: string;                 // 动态，不枚举（开闭原则）
  metricName: string;
  score: number;                     // 0~1
  weight: number;
  reasoning: string | null;
  judgeType: string;                 // rule | llm | 插件类型
}
// 分组规则：按 judgeType 分组展示；同 metricKey 多 Judge 都展示（对齐后端聚合逻辑）
```

### 2.4 TimelineItemVM（Trace 时间线）

```typescript
// 后端 /timeline 已返回算好的 events（start_ms/duration_ms/depth，api-contract §1.4 已实测）
// 前端仅做字段命名映射（snake → camel），禁止重复计算 offset/depth
interface TimelineItemVM {
  spanId: string;                    // ← span_id
  name: string;
  kind: string;                      // ← span_type：root | llm_call | tool_call | ...（动态）
  startOffsetMs: number;             // ← start_ms（后端已算）
  durationMs: number;                // ← duration_ms
  depth: number;                     // ← depth（后端已算）→ 泳道行
  status: 'ok' | 'error';
  label: string;
}
// 转换：data.events 逐项映射 + data.total_duration_ms 作 X 轴量程 → ECharts custom series
```

### 2.5 ScenarioDiffVM（回归对比行）

```typescript
interface ScenarioDiffVM {
  scenarioTitle: string;
  externalId: string;
  baselineScore: number | null;
  targetScore: number | null;
  scoreDelta: number | null;         // 高亮规则：delta<0 红色，>0 绿色
  verdict: 'improved' | 'regressed' | 'unchanged' | 'flaky';
  metricDeltas: Record<string, number>;  // 动态指标，展开行渲染
}
```

## 3. 展示映射表（组件层唯一映射真相）

### 3.1 状态 → 颜色/文案

| status | antd color | 中文 |
|--------|-----------|------|
| pending | default | 等待中 |
| running | processing | 执行中 |
| completed | success | 已完成 |
| failed | error | 失败 |
| cancelled / skipped | warning | 已取消/跳过 |
| timeout | error | 超时 |

### 3.2 verdict → 展示

| verdict | 颜色 | 图标语义 |
|---------|------|---------|
| pass / improved | green | ✓ |
| partial / unchanged | gold | ~ |
| fail / regressed | red | ✗ |
| flaky | purple | ⚡ |

### 3.3 分数格式化规则

- 分数一律保留 2 位小数展示（`0.85`），百分比场景 `85%`
- score ≥ 0.8 绿色、≥ 0.5 金色、< 0.5 红色（对齐后端 verdict 阈值）
