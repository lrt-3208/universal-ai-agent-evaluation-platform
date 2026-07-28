/**
 * Evaluation 详情页 — F3.4
 *
 * Reference: docs/phases/phase-f3-evaluation.md §2.3
 * 头部状态轮询（useEvaluationStatus）+ Tab（executions 默认 | trace/reports F5 占位）
 */
import { useMemo, useState } from 'react';
import {
  App,
  Button,
  Card,
  Col,
  Drawer,
  Descriptions,
  Popconfirm,
  Progress,
  Row,
  Space,
  Statistic,
  Table,
  Tabs,
  Typography,
} from 'antd';
import { useParams, useSearchParams } from 'react-router-dom';
import {
  useCancelEvaluation,
  useEvaluation,
  useEvaluationStatus,
  useExecutions,
  useExecutionDetail,
} from '@/hooks/useEvaluations';
import { useJudgeResults, useLatestReportSnapshot, useTriggerJudge } from '@/hooks/useJudge';
import { JudgeResultCard, MetricRadar } from '@/components/judge';
import TraceTab from '@/pages/trace/TraceTab';
import ReportsTab from '@/pages/report/ReportsTab';
import { useScenarios } from '@/hooks/useDatasetScenario';
import { toProgress } from '@/types/evaluation';
import { NotFoundResult, QueryBoundary, StatusTag } from '@/components/common';
import { ApiError } from '@/api/client';
import { bizTokens } from '@/theme/tokens';
import { formatScore, scoreColor } from '@/utils/score';
import type { ConversationMessage } from '@/api/endpoints/evaluations';

export default function EvaluationDetailPage() {
  const { evalId } = useParams<{ evalId: string }>();
  const { message } = App.useApp();
  // Tab 状态入 searchParams（route-map §1）
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get('tab') ?? 'executions';

  const evalQuery = useEvaluation(evalId ?? null);
  const { data: statusData, isPolling } = useEvaluationStatus(evalId ?? null);
  const cancelMut = useCancelEvaluation();
  const triggerJudgeMut = useTriggerJudge(evalId ?? '');

  if (!evalId) return <NotFoundResult />;

  const progress = statusData ? toProgress(statusData) : null;
  const isTerminal = !isPolling && !!statusData;

  const handleCancel = async () => {
    try {
      await cancelMut.mutateAsync(evalId);
      message.success('评测已取消');
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    }
  };

  const handleTriggerJudge = async () => {
    try {
      await triggerJudgeMut.mutateAsync();
      message.success('评分已发起');
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    }
  };

  return (
    <QueryBoundary query={evalQuery}>
      {(evaluation) => (
        <div>
          {/* 头部：状态 + 进度 + 操作 */}
          <Card style={{ marginBottom: 16 }}>
            <Row gutter={24} align="middle">
              <Col flex="auto">
                <Space direction="vertical" size={4}>
                  <Space>
                    <Typography.Title level={4} style={{ margin: 0 }}>
                      {evaluation.name}
                    </Typography.Title>
                    <StatusTag status={statusData?.status ?? evaluation.status} />
                    {evaluation.version_label && (
                      <Typography.Text type="secondary">{evaluation.version_label}</Typography.Text>
                    )}
                  </Space>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    创建于 {new Date(evaluation.created_at).toLocaleString()}
                    {isPolling && ' · 实时刷新中'}
                  </Typography.Text>
                </Space>
              </Col>
              <Col>
                <Space size={24}>
                  {progress && (
                    <Progress
                      type="circle"
                      size={64}
                      percent={progress.percent}
                      format={() => `${progress.done}/${progress.total}`}
                      data-testid="progress-ring"
                    />
                  )}
                  {statusData && (
                    <Space size={16}>
                      <Statistic title="完成" value={statusData.completed} />
                      <Statistic title="失败" value={statusData.failed} />
                      <Statistic title="待执行" value={statusData.pending + statusData.running} />
                    </Space>
                  )}
                  {['pending', 'running'].includes(statusData?.status ?? evaluation.status) && (
                    <Popconfirm title="确认取消该评测？" onConfirm={handleCancel}>
                      <Button danger>取消评测</Button>
                    </Popconfirm>
                  )}
                  {isTerminal && (
                    <Button
                      onClick={handleTriggerJudge}
                      loading={triggerJudgeMut.isPending}
                      data-testid="trigger-judge-btn"
                    >
                      发起评分
                    </Button>
                  )}
                </Space>
              </Col>
            </Row>
          </Card>

          {/* 概览区：pass_rate + 指标雷达图（F4.3，数据源=报告 metrics_snapshot） */}
          {isTerminal && <OverviewSection evaluationId={evalId} />}

          <Tabs
            activeKey={tab}
            onChange={(key) => setSearchParams({ tab: key })}
            items={[
              {
                key: 'executions',
                label: '场景执行',
                children: (
                  <ExecutionsTab
                    evaluationId={evalId}
                    datasetId={evaluation.dataset_id}
                    isRunning={isPolling}
                  />
                ),
              },
              {
                key: 'trace',
                label: 'Trace',
                children: <TraceTab evaluationId={evalId} datasetId={evaluation.dataset_id} />,
              },
              {
                key: 'reports',
                label: '报告',
                children: <ReportsTab evaluationId={evalId} />,
              },
            ]}
          />
        </div>
      )}
    </QueryBoundary>
  );
}

/** 概览区：pass_rate（executions 聚合）+ 指标雷达图（报告 metrics_snapshot） */
function OverviewSection({ evaluationId }: { evaluationId: string }) {
  const execQuery = useExecutions(evaluationId, false);
  const reportQuery = useLatestReportSnapshot(evaluationId);

  const execs = execQuery.data ?? [];
  const scored = execs.filter((e) => e.overall_verdict != null);
  const passRate = scored.length > 0
    ? scored.filter((e) => e.overall_verdict === 'pass').length / scored.length
    : null;
  const avgScore = scored.length > 0
    ? scored.reduce((sum, e) => sum + (e.overall_score ?? 0), 0) / scored.length
    : null;

  return (
    <Card style={{ marginBottom: 16 }} size="small" title="评分概览">
      <Row gutter={24} align="middle">
        <Col span={8}>
          <Space size={32}>
            <Statistic
              title="通过率"
              value={passRate != null ? (passRate * 100).toFixed(0) : '-'}
              suffix={passRate != null ? '%' : ''}
              valueStyle={passRate != null ? { color: scoreColor(passRate) } : undefined}
            />
            <Statistic
              title="平均分"
              value={formatScore(avgScore)}
              valueStyle={avgScore != null ? { color: scoreColor(avgScore) } : undefined}
            />
            <Statistic title="已评分" value={`${scored.length}/${execs.length}`} />
          </Space>
        </Col>
        <Col span={16}>
          <MetricRadar report={reportQuery.data ?? null} />
        </Col>
      </Row>
    </Card>
  );
}

/** 执行列表 Tab（含对话抽屉） */
function ExecutionsTab({
  evaluationId,
  datasetId,
  isRunning,
}: {
  evaluationId: string;
  datasetId: string;
  isRunning: boolean;
}) {
  const execQuery = useExecutions(evaluationId, isRunning);
  // scenario_id → 标题映射（执行列表不含场景标题，用场景列表补全，上限 100）
  const scenariosQuery = useScenarios(datasetId, 1, 100);
  const [viewingExecId, setViewingExecId] = useState<string | null>(null);
  const detailQuery = useExecutionDetail(evaluationId, viewingExecId);

  const titleMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of scenariosQuery.data?.items ?? []) map.set(s.id, s.title);
    return map;
  }, [scenariosQuery.data]);

  return (
    <>
      <QueryBoundary query={execQuery} isEmpty={(d) => d.length === 0} emptyText="暂无执行记录">
        {(execs) => (
          <Table
            rowKey="id"
            dataSource={execs}
            pagination={false}
            columns={[
              {
                title: '场景',
                dataIndex: 'scenario_id',
                render: (sid: string, e) => (
                  <a onClick={() => setViewingExecId(e.id)} data-testid="exec-row-link">
                    {titleMap.get(sid) ?? sid.slice(0, 8)}
                  </a>
                ),
              },
              {
                title: '状态',
                dataIndex: 'status',
                width: 100,
                render: (s: string) => <StatusTag status={s} />,
              },
              {
                title: '总分',
                dataIndex: 'overall_score',
                width: 90,
                render: (v: number | null) => (v != null ? v.toFixed(2) : '-'),
              },
              {
                title: '判定',
                dataIndex: 'overall_verdict',
                width: 100,
                render: (v: string | null) => <StatusTag status={v} />,
              },
              {
                title: '重试',
                dataIndex: 'retry_count',
                width: 70,
              },
              {
                title: '错误',
                dataIndex: 'error_message',
                ellipsis: true,
                render: (v: string | null) => v ?? '-',
              },
            ]}
          />
        )}
      </QueryBoundary>

      {/* 对话抽屉 */}
      <Drawer
        title="执行详情"
        width={560}
        open={!!viewingExecId}
        onClose={() => setViewingExecId(null)}
        destroyOnHidden
      >
        <QueryBoundary query={detailQuery}>
          {(exec) => (
            <div>
              <Descriptions column={2} size="small" style={{ marginBottom: 16 }}>
                <Descriptions.Item label="状态">
                  <StatusTag status={exec.status} />
                </Descriptions.Item>
                <Descriptions.Item label="耗时">
                  {exec.latency_ms != null ? `${exec.latency_ms} ms` : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="Adapter">{exec.agent_adapter_type}</Descriptions.Item>
                <Descriptions.Item label="Tokens">
                  {exec.conversation_data?.total_tokens
                    ? `${exec.conversation_data.total_tokens.prompt ?? 0} / ${exec.conversation_data.total_tokens.completion ?? 0}`
                    : '-'}
                </Descriptions.Item>
              </Descriptions>

              <Typography.Title level={5}>对话内容</Typography.Title>
              <div data-testid="conversation">
                {(exec.conversation_data?.messages ?? []).map((m, i) => (
                  <MessageBubble key={i} message={m} />
                ))}
              </div>

              {/* 评分区（F4.2）：按 Judge 分组，动态指标 */}
              <Typography.Title level={5} style={{ marginTop: 16 }}>
                评分结果
              </Typography.Title>
              <JudgeResultsSection scenarioExecutionId={exec.scenario_execution_id} />
            </div>
          )}
        </QueryBoundary>
      </Drawer>
    </>
  );
}

/** 评分结果区：GET /scenario-executions/{id}/judge-results */
function JudgeResultsSection({ scenarioExecutionId }: { scenarioExecutionId: string }) {
  const query = useJudgeResults(scenarioExecutionId);
  return (
    <QueryBoundary query={query} isEmpty={(d) => d.length === 0} emptyText="暂无评分（可在页面头部发起评分）">
      {(results) => (
        <div data-testid="judge-results-section">
          {results.map((r) => (
            <JudgeResultCard key={r.id} result={r} />
          ))}
        </div>
      )}
    </QueryBoundary>
  );
}

/** 对话气泡：user 右 / assistant 左（phase-f3 §2.3） */
function MessageBubble({ message }: { message: ConversationMessage }) {
  const isUser = message.role === 'user';
  return (
    <div style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', marginBottom: 8 }}>
      <div
        style={{
          maxWidth: '80%',
          padding: '8px 12px',
          borderRadius: 8,
          background: isUser ? '#2F54EB' : '#f5f5f5',
          color: isUser ? '#fff' : 'inherit',
          fontFamily: bizTokens.fontFamilyCode,
          fontSize: 13,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        <Typography.Text style={{ fontSize: 11, color: isUser ? '#d6e0ff' : '#999' }}>
          {message.role}
        </Typography.Text>
        <div style={{ color: 'inherit' }}>{message.content}</div>
      </div>
    </div>
  );
}
