/**
 * Regression 列表页 + 详情页 — F6.2/6.3
 *
 * Reference: docs/phases/phase-f6-regression.md §2.2/2.3
 */
import { useState } from 'react';
import {
  App,
  Button,
  Card,
  Col,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import { EyeOutlined, PlusOutlined, RedoOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useRegression, useRegressions, useReplayEvaluation } from '@/hooks/useRegressions';
import { regressionReportUrl } from '@/api/endpoints/regressions';
import type { MetricDiff, ScenarioDiff } from '@/api/endpoints/regressions';
import { NotFoundResult, QueryBoundary, StatusTag } from '@/components/common';
import { formatScore } from '@/utils/score';
import { bizTokens } from '@/theme/tokens';
import { ApiError } from '@/api/client';

/** regression_risk → 颜色 */
const RISK_COLOR: Record<string, string> = {
  low: 'green',
  medium: 'gold',
  high: 'orange',
  critical: 'red',
};

/** delta 色阶：负红正绿（AC-F6-04） */
function deltaStyle(delta: number | null): React.CSSProperties {
  if (delta == null || delta === 0) return {};
  return { color: delta < 0 ? bizTokens.colorScoreLow : bizTokens.colorScoreHigh, fontWeight: 600 };
}

// ============================================================
// 列表页
// ============================================================

export function RegressionListPage() {
  const { projId } = useParams<{ projId: string }>();
  const navigate = useNavigate();
  const query = useRegressions(projId ?? null);

  if (!projId) return <NotFoundResult />;

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          回归对比
        </Typography.Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate(`/projects/${projId}/regressions/new`)}
          data-testid="new-regression-btn"
        >
          创建对比
        </Button>
      </Space>

      <QueryBoundary query={query} isEmpty={(d) => d.length === 0} emptyText="暂无回归分析">
        {(items) => (
          <Table
            rowKey="id"
            dataSource={items}
            pagination={false}
            columns={[
              {
                title: '名称',
                dataIndex: 'name',
                render: (n: string, r) => <a onClick={() => navigate(`/regressions/${r.id}`)}>{n}</a>,
              },
              {
                title: '结论',
                dataIndex: 'overall_verdict',
                width: 110,
                render: (v: string | null) => <StatusTag status={v} />,
              },
              {
                title: '风险',
                width: 100,
                render: (_, r) => {
                  const risk = r.summary?.regression_risk;
                  return risk ? <Tag color={RISK_COLOR[risk]}>{risk}</Tag> : '-';
                },
              },
              {
                title: '回归/改进/不变',
                width: 140,
                render: (_, r) =>
                  r.summary
                    ? `${r.summary.regressed} / ${r.summary.improved} / ${r.summary.unchanged}`
                    : '-',
              },
              {
                title: '创建时间',
                dataIndex: 'created_at',
                width: 180,
                render: (t: string) => new Date(t).toLocaleString(),
              },
            ]}
          />
        )}
      </QueryBoundary>
    </div>
  );
}

// ============================================================
// 详情页
// ============================================================

export function RegressionDetailPage() {
  const { regId } = useParams<{ regId: string }>();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const query = useRegression(regId ?? null);
  const replayMut = useReplayEvaluation();

  const [verdictFilter, setVerdictFilter] = useState<string>('all');
  const [reportOpen, setReportOpen] = useState(false);
  const [replayOpen, setReplayOpen] = useState(false);
  const [replayForm] = Form.useForm();

  if (!regId) return <NotFoundResult />;

  const handleReplay = async (baselineEvalId: string) => {
    const values = await replayForm.validateFields();
    try {
      const result = await replayMut.mutateAsync({
        evaluationId: baselineEvalId,
        agentConfig: { adapter_type: values.adapter_type, endpoint: values.endpoint },
      });
      message.success('回放评测已创建');
      navigate(`/evaluations/${result.evaluation_id}`);
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    }
  };

  return (
    <QueryBoundary query={query}>
      {(reg) => {
        const diffs = reg.scenario_diffs ?? [];
        // regressed 置顶（AC-F6-04），其余按 external_id
        const sorted = [...diffs].sort((a, b) => {
          const pa = a.verdict === 'regressed' ? 0 : 1;
          const pb = b.verdict === 'regressed' ? 0 : 1;
          return pa - pb || a.external_id.localeCompare(b.external_id);
        });
        const filtered =
          verdictFilter === 'all' ? sorted : sorted.filter((d) => d.verdict === verdictFilter);
        const metricDiffs = Object.entries(reg.metric_diffs ?? {});

        return (
          <div>
            {/* 摘要区 */}
            <Card style={{ marginBottom: 16 }}>
              <Space style={{ width: '100%', justifyContent: 'space-between' }} align="start">
                <Space direction="vertical" size={4}>
                  <Space>
                    <Typography.Title level={4} style={{ margin: 0 }}>
                      {reg.name}
                    </Typography.Title>
                    <StatusTag status={reg.overall_verdict} />
                    {reg.summary && (
                      <Tag color={RISK_COLOR[reg.summary.regression_risk]} data-testid="risk-tag">
                        风险: {reg.summary.regression_risk}
                      </Tag>
                    )}
                  </Space>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {new Date(reg.created_at).toLocaleString()}
                  </Typography.Text>
                </Space>
                <Space>
                  <Button icon={<EyeOutlined />} onClick={() => setReportOpen(true)} data-testid="view-diff-report-btn">
                    Diff 报告
                  </Button>
                  <Button icon={<RedoOutlined />} onClick={() => setReplayOpen(true)} data-testid="replay-btn">
                    Dataset 回放
                  </Button>
                </Space>
              </Space>
              {reg.summary && (
                <Row gutter={24} style={{ marginTop: 16 }} data-testid="summary-stats">
                  <Col><Statistic title="对比场景" value={reg.summary.total_compared} /></Col>
                  <Col><Statistic title="改进" value={reg.summary.improved} valueStyle={{ color: bizTokens.colorScoreHigh }} /></Col>
                  <Col><Statistic title="回归" value={reg.summary.regressed} valueStyle={{ color: bizTokens.colorScoreLow }} /></Col>
                  <Col><Statistic title="无变化" value={reg.summary.unchanged} /></Col>
                  <Col><Statistic title="不稳定" value={reg.summary.flaky} valueStyle={{ color: bizTokens.colorFlaky }} /></Col>
                </Row>
              )}
            </Card>

            {/* 指标级 Diff */}
            <Card title="指标级差异" size="small" style={{ marginBottom: 16 }}>
              <Table
                rowKey={([k]) => k}
                dataSource={metricDiffs}
                pagination={false}
                size="small"
                data-testid="metric-diff-table"
                columns={[
                  { title: '指标', render: (_, [k]) => k },
                  { title: 'Baseline 均值', render: (_, [, v]: [string, MetricDiff]) => formatScore(v.baseline_mean) },
                  { title: 'Target 均值', render: (_, [, v]: [string, MetricDiff]) => formatScore(v.target_mean) },
                  {
                    title: 'Delta',
                    render: (_, [, v]: [string, MetricDiff]) => (
                      <span style={deltaStyle(v.delta)}>{v.delta > 0 ? '+' : ''}{v.delta.toFixed(4)}</span>
                    ),
                  },
                  { title: '方向', render: (_, [, v]: [string, MetricDiff]) => <StatusTag status={v.direction} /> },
                  { title: '受影响场景', render: (_, [, v]: [string, MetricDiff]) => v.affected_count },
                ]}
              />
            </Card>

            {/* 场景级 Diff */}
            <Card
              title="场景级差异"
              size="small"
              extra={
                <Select
                  size="small"
                  style={{ width: 140 }}
                  value={verdictFilter}
                  onChange={setVerdictFilter}
                  options={[
                    { value: 'all', label: '全部' },
                    { value: 'regressed', label: '回归' },
                    { value: 'improved', label: '改进' },
                    { value: 'unchanged', label: '无变化' },
                    { value: 'flaky', label: '不稳定' },
                  ]}
                  data-testid="verdict-filter"
                />
              }
            >
              <Table
                rowKey="scenario_id"
                dataSource={filtered}
                pagination={false}
                size="small"
                data-testid="scenario-diff-table"
                rowClassName={(d: ScenarioDiff) => (d.verdict === 'regressed' ? 'regressed-row' : '')}
                onRow={(d) =>
                  d.verdict === 'regressed' ? { style: { background: '#fff1f0' } } : {}
                }
                expandable={{
                  // 展开行：动态 metricDeltas（AC-F6-05）
                  expandedRowRender: (d: ScenarioDiff) => (
                    <Space size={16} data-testid="metric-deltas-detail">
                      {Object.entries(d.metric_deltas ?? {}).map(([k, v]) => (
                        <Typography.Text key={k} style={{ fontSize: 12 }}>
                          {k}: <span style={deltaStyle(v)}>{v > 0 ? '+' : ''}{v.toFixed(4)}</span>
                        </Typography.Text>
                      ))}
                      {d.notes && (
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          {d.notes}
                        </Typography.Text>
                      )}
                    </Space>
                  ),
                }}
                columns={[
                  { title: '场景', dataIndex: 'title' },
                  { title: 'ID', dataIndex: 'external_id', width: 100 },
                  { title: 'Baseline', width: 90, render: (_, d) => formatScore(d.baseline_score) },
                  { title: 'Target', width: 90, render: (_, d) => formatScore(d.target_score) },
                  {
                    title: 'Delta',
                    width: 100,
                    render: (_, d) =>
                      d.score_delta != null ? (
                        <span style={deltaStyle(d.score_delta)}>
                          {d.score_delta > 0 ? '+' : ''}
                          {d.score_delta.toFixed(4)}
                        </span>
                      ) : (
                        '-'
                      ),
                  },
                  {
                    title: '判定',
                    dataIndex: 'verdict',
                    width: 100,
                    render: (v: string) => <StatusTag status={v} />,
                  },
                ]}
              />
            </Card>

            {/* Diff 报告预览 Modal */}
            <Modal
              title="Diff 报告"
              open={reportOpen}
              onCancel={() => setReportOpen(false)}
              footer={null}
              width="80%"
              style={{ top: 32 }}
              destroyOnHidden
            >
              <iframe
                src={regressionReportUrl(reg.id)}
                style={{ width: '100%', height: '70vh', border: 'none' }}
                title="diff-report"
                data-testid="diff-report-iframe"
              />
            </Modal>

            {/* Dataset 回放 Modal */}
            <Modal
              title="Dataset 回放（使用新 Agent 配置重新评测）"
              open={replayOpen}
              onOk={() => handleReplay(reg.baseline_evaluation_id)}
              onCancel={() => setReplayOpen(false)}
              confirmLoading={replayMut.isPending}
              destroyOnHidden
            >
              <Form form={replayForm} layout="vertical" initialValues={{ adapter_type: 'http' }}>
                <Form.Item name="adapter_type" label="Adapter 类型" rules={[{ required: true }]}>
                  <Select
                    options={[
                      { value: 'http', label: 'HTTP' },
                      { value: 'openai', label: 'OpenAI 兼容' },
                      { value: 'custom', label: 'Custom' },
                    ]}
                  />
                </Form.Item>
                <Form.Item
                  name="endpoint"
                  label="新 Agent Endpoint"
                  rules={[{ required: true, message: '请输入 endpoint' }]}
                  tooltip="base URL，不带 /chat"
                >
                  <Input placeholder="http://localhost:9001" data-testid="replay-endpoint-input" />
                </Form.Item>
              </Form>
            </Modal>
          </div>
        );
      }}
    </QueryBoundary>
  );
}

export default RegressionListPage;
