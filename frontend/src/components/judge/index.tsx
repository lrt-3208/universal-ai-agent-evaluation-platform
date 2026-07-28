/**
 * Judge 业务组件 — F4
 *
 * JudgeConfigForm: 多 Judge 配置卡片（向导 Step3）
 * JudgeResultCard: 按 Judge 分组的评分展示（动态 metric_key，开闭原则）
 * MetricRadar: 指标雷达图（数据源 = report metrics_snapshot）
 *
 * Reference: docs/phases/phase-f4-judge.md
 */
import { useMemo } from 'react';
import {
  Alert,
  Button,
  Card,
  Collapse,
  Empty,
  InputNumber,
  Progress,
  Select,
  Space,
  Tag,
  Typography,
} from 'antd';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { JudgeConfig } from '@/api/endpoints/evaluations';
import type { JudgeResult, MetricsSnapshot } from '@/api/endpoints/judges';
import { StatusTag } from '@/components/common';
import { formatScore, scoreColor } from '@/utils/score';
import { bizTokens } from '@/theme/tokens';

// ---------------- 内置 Judge 元数据（F7 后与插件合并 — useAvailableJudgeTypes） ----------------

/** 内置 judge 类型与其支持的指标（对齐后端 supported_metrics） */
export const BUILTIN_JUDGES: Record<string, { label: string; metrics: string[] }> = {
  rule: {
    label: 'Rule Judge（规则匹配）',
    metrics: ['correctness', 'forbidden_check', 'tool_accuracy', 'intent_match'],
  },
  llm: {
    label: 'LLM Judge（语义评分）',
    metrics: ['correctness', 'hallucination', 'coherence', 'planning_score', 'memory_accuracy'],
  },
};

// ---------------- JudgeConfigForm ----------------

interface JudgeConfigFormProps {
  value: JudgeConfig[];
  onChange: (configs: JudgeConfig[]) => void;
  /** validate API 返回的错误（内联展示） */
  errors?: string[];
  warnings?: string[];
  /** judge_type 下拉选项（F7：内置 ∪ enabled 插件，useAvailableJudgeTypes 提供）；缺省用内置 */
  typeOptions?: { value: string; label: string }[];
}

export function JudgeConfigForm({ value, onChange, errors, warnings, typeOptions }: JudgeConfigFormProps) {
  const update = (idx: number, patch: Partial<JudgeConfig>) => {
    onChange(value.map((c, i) => (i === idx ? { ...c, ...patch } : c)));
  };
  const options =
    typeOptions ?? Object.entries(BUILTIN_JUDGES).map(([k, v]) => ({ value: k, label: v.label }));

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={12}>
      {value.map((config, idx) => {
        const meta = BUILTIN_JUDGES[config.judge_type];
        return (
          <Card
            key={idx}
            size="small"
            title={
              <Space>
                <Tag color="blue">{config.judge_type}</Tag>
                Judge #{idx + 1}
              </Space>
            }
            extra={
              <Button
                type="text"
                danger
                size="small"
                icon={<DeleteOutlined />}
                onClick={() => onChange(value.filter((_, i) => i !== idx))}
              />
            }
          >
            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <div>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  Judge 类型
                </Typography.Text>
                <Select
                  style={{ width: '100%' }}
                  value={config.judge_type}
                  onChange={(t) =>
                    update(idx, {
                      judge_type: t,
                      // 插件 judge 无内置指标元数据 → 置空由插件自行决定
                      metrics: BUILTIN_JUDGES[t] ? [BUILTIN_JUDGES[t].metrics[0]] : [],
                    })
                  }
                  options={options}
                  data-testid={`judge-type-select-${idx}`}
                />
              </div>
              <div>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  评估指标
                </Typography.Text>
                <Select
                  mode="multiple"
                  style={{ width: '100%' }}
                  value={config.metrics ?? []}
                  onChange={(m) => update(idx, { metrics: m })}
                  options={(meta?.metrics ?? []).map((m) => ({ value: m, label: m }))}
                  placeholder="选择指标"
                  data-testid={`judge-metrics-select-${idx}`}
                />
              </div>
              <div>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  权重（选中指标，默认 1.0）
                </Typography.Text>
                <Space wrap>
                  {(config.metrics ?? []).map((m) => (
                    <Space key={m} size={4}>
                      <Typography.Text style={{ fontSize: 12 }}>{m}</Typography.Text>
                      <InputNumber
                        size="small"
                        min={0}
                        max={10}
                        step={0.1}
                        value={config.weights?.[m] ?? 1.0}
                        onChange={(w) =>
                          update(idx, { weights: { ...(config.weights ?? {}), [m]: w ?? 1.0 } })
                        }
                      />
                    </Space>
                  ))}
                </Space>
              </div>
            </Space>
          </Card>
        );
      })}

      <Button
        block
        type="dashed"
        icon={<PlusOutlined />}
        onClick={() => onChange([...value, { judge_type: 'rule', metrics: ['correctness'] }])}
        data-testid="add-judge-btn"
      >
        添加 Judge
      </Button>

      {/* validate 错误内联展示（AC-F4-02） */}
      {errors && errors.length > 0 && (
        <Alert
          type="error"
          showIcon
          message="Judge 配置校验失败"
          description={errors.map((e, i) => (
            <div key={i}>{e}</div>
          ))}
          data-testid="judge-validate-errors"
        />
      )}
      {warnings && warnings.length > 0 && (
        <Alert type="warning" showIcon message={warnings.join('；')} />
      )}
      {value.some((c) => c.judge_type === 'llm') && (
        <Alert
          type="info"
          showIcon
          message="LLM Judge 依赖后端 .env 中的 LLM 配置（LLM_API_KEY 等）"
        />
      )}
    </Space>
  );
}

// ---------------- JudgeResultCard ----------------

/** 按 Judge 分组的评分卡：动态渲染任意 metric_key（禁止硬编码指标枚举） */
export function JudgeResultCard({ result }: { result: JudgeResult }) {
  return (
    <Card
      size="small"
      style={{ marginBottom: 8 }}
      title={
        <Space>
          <Tag color="blue">{result.judge_type}</Tag>
          {result.overall_score != null && (
            <span style={{ color: scoreColor(result.overall_score), fontWeight: 600 }}>
              {formatScore(result.overall_score)}
            </span>
          )}
          <StatusTag status={result.overall_verdict} />
        </Space>
      }
      extra={<StatusTag status={result.status} />}
      data-testid="judge-result-card"
    >
      {result.status === 'failed' ? (
        <Alert type="error" message={result.error_message ?? '评分失败'} />
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size={4}>
          {result.metric_scores.map((ms) => (
            <div key={ms.metric_key} data-testid="metric-score-row">
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Typography.Text style={{ fontSize: 13 }}>{ms.metric_key}</Typography.Text>
                <Typography.Text style={{ fontSize: 13, color: scoreColor(ms.score) }}>
                  {formatScore(ms.score)}（权重 {ms.weight}）
                </Typography.Text>
              </Space>
              <Progress
                percent={ms.score * 100}
                showInfo={false}
                strokeColor={scoreColor(ms.score)}
                size="small"
              />
              {ms.reasoning && (
                <Collapse
                  ghost
                  size="small"
                  items={[
                    {
                      key: '1',
                      label: (
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          评分理由
                        </Typography.Text>
                      ),
                      children: (
                        <Typography.Paragraph style={{ fontSize: 12, marginBottom: 0 }}>
                          {ms.reasoning}
                        </Typography.Paragraph>
                      ),
                    },
                  ]}
                />
              )}
            </div>
          ))}
        </Space>
      )}
    </Card>
  );
}

// ---------------- MetricRadar ----------------

/** 指标雷达图：指标轴动态生成自 metrics_snapshot.metric_aggregates（AC-F4-06） */
export function MetricRadar({ report }: { report: { metrics_snapshot: unknown } | null }) {
  const option = useMemo(() => {
    const snapshot = (report?.metrics_snapshot ?? null) as MetricsSnapshot | null;
    const aggregates = snapshot?.metric_aggregates ?? {};
    const keys = Object.keys(aggregates);
    if (keys.length === 0) return null;
    return {
      radar: {
        indicator: keys.map((k) => ({ name: k, max: 1 })),
        radius: '65%',
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: keys.map((k) => aggregates[k].mean),
              name: '指标均值',
              areaStyle: { opacity: 0.2 },
              lineStyle: { color: bizTokens.colorTraceLLM },
            },
          ],
        },
      ],
      tooltip: {},
    };
  }, [report]);

  if (!option) {
    return (
      <Empty
        description="生成报告后查看指标分布"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        data-testid="radar-empty-hint"
      />
    );
  }
  return <ReactECharts option={option} style={{ height: 260 }} notMerge data-testid="metric-radar" />;
}
