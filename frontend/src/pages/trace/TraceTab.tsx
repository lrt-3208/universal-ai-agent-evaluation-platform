/**
 * Trace Tab — F5.2
 *
 * 左侧执行选择 + 右侧 Trace 视图（时间线甘特图 / 树模式切换）
 * Reference: docs/phases/phase-f5-trace-report.md §2.1
 */
import { useMemo, useState } from 'react';
import { Card, Col, Empty, Menu, Radio, Row, Space, Tag, Tree, Typography } from 'antd';
import ReactECharts from 'echarts-for-react';
import { useExecutionTrace, useTimeline } from '@/hooks/useTraceReport';
import { useExecutions } from '@/hooks/useEvaluations';
import { useScenarios } from '@/hooks/useDatasetScenario';
import { toTimelineVM } from '@/types/timeline';
import type { TraceSpanNode } from '@/api/endpoints/traces';
import { QueryBoundary, StatusTag } from '@/components/common';
import { bizTokens } from '@/theme/tokens';

/** span kind → 颜色（design-tokens §2.2，映射表驱动） */
function kindColor(kind: string): string {
  if (kind === 'llm_call') return bizTokens.colorTraceLLM;
  if (kind === 'tool_call') return bizTokens.colorTraceTool;
  return bizTokens.colorTraceOther;
}

export default function TraceTab({
  evaluationId,
  datasetId,
}: {
  evaluationId: string;
  datasetId: string;
}) {
  const execQuery = useExecutions(evaluationId, false);
  const scenariosQuery = useScenarios(datasetId, 1, 100);
  const [selectedExecId, setSelectedExecId] = useState<string | null>(null);
  const [mode, setMode] = useState<'timeline' | 'tree'>('timeline');

  const titleMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of scenariosQuery.data?.items ?? []) map.set(s.id, s.title);
    return map;
  }, [scenariosQuery.data]);

  const execs = execQuery.data ?? [];
  const activeExecId = selectedExecId ?? execs[0]?.id ?? null;

  return (
    <Row gutter={16}>
      <Col span={6}>
        <Card size="small" title="选择执行">
          <Menu
            mode="inline"
            style={{ border: 'none' }}
            selectedKeys={activeExecId ? [activeExecId] : []}
            onClick={({ key }) => setSelectedExecId(key)}
            items={execs.map((e) => ({
              key: e.id,
              label: (
                <Space>
                  {titleMap.get(e.scenario_id) ?? e.scenario_id.slice(0, 8)}
                  <StatusTag status={e.status} />
                </Space>
              ),
            }))}
          />
        </Card>
      </Col>
      <Col span={18}>
        <Card
          size="small"
          title="Trace"
          extra={
            <Radio.Group
              size="small"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              options={[
                { value: 'timeline', label: '时间线' },
                { value: 'tree', label: '树' },
              ]}
              optionType="button"
              data-testid="trace-mode-switch"
            />
          }
        >
          {activeExecId ? (
            <TraceView evaluationId={evaluationId} execId={activeExecId} mode={mode} />
          ) : (
            <Empty description="暂无执行" />
          )}
        </Card>
      </Col>
    </Row>
  );
}

function TraceView({
  evaluationId,
  execId,
  mode,
}: {
  evaluationId: string;
  execId: string;
  mode: 'timeline' | 'tree';
}) {
  const traceQuery = useExecutionTrace(evaluationId, execId);

  if (traceQuery.isError) {
    // 无 Trace → 404 → EmptyState（AC-F5-08）
    return <Empty description="该执行未产生 Trace" data-testid="trace-empty" />;
  }

  return (
    <QueryBoundary query={traceQuery}>
      {(trace) =>
        mode === 'timeline' ? (
          <TimelineChart traceId={trace.id} />
        ) : (
          <SpanTree root={trace.span_tree} />
        )
      }
    </QueryBoundary>
  );
}

/** 时间线甘特图：ECharts custom series，X=相对时间(ms)，Y=depth 泳道 */
function TimelineChart({ traceId }: { traceId: string }) {
  const timelineQuery = useTimeline(traceId);

  const option = useMemo(() => {
    if (!timelineQuery.data) return null;
    const vm = toTimelineVM(timelineQuery.data);
    if (vm.items.length === 0) return null;

    return {
      grid: { left: 90, right: 30, top: 10, bottom: 30 },
      xAxis: {
        type: 'value',
        max: vm.totalDurationMs,
        axisLabel: { formatter: '{value} ms' },
      },
      yAxis: {
        type: 'category',
        data: Array.from({ length: vm.maxDepth + 1 }, (_, i) => `depth ${i}`),
        inverse: true,
      },
      tooltip: {
        formatter: (p: { data: { vm: (typeof vm.items)[0] } }) => {
          const item = p.data.vm;
          return `${item.label}<br/>类型: ${item.kind}<br/>耗时: ${item.durationMs} ms<br/>状态: ${item.status}`;
        },
      },
      series: [
        {
          type: 'custom',
          encode: { x: [1, 2], y: 0 },
          data: vm.items.map((item) => ({
            value: [item.depth, item.startOffsetMs, item.startOffsetMs + item.durationMs],
            vm: item,
            itemStyle: {
              color: kindColor(item.kind),
              // error span 红色描边（phase-f5 §2.1）
              borderColor: item.status === 'error' ? bizTokens.colorScoreLow : undefined,
              borderWidth: item.status === 'error' ? 2 : 0,
            },
          })),
          renderItem: (
            _params: unknown,
            api: {
              value: (i: number) => number;
              coord: (v: number[]) => number[];
              size: (v: number[]) => number[];
              style: () => Record<string, unknown>;
            },
          ) => {
            const depth = api.value(0);
            const start = api.coord([api.value(1), depth]);
            const end = api.coord([api.value(2), depth]);
            const height = 18;
            return {
              type: 'rect',
              shape: {
                x: start[0],
                y: start[1] - height / 2,
                width: Math.max(end[0] - start[0], 2),
                height,
                r: 3,
              },
              style: api.style(),
            };
          },
        },
      ],
    };
  }, [timelineQuery.data]);

  if (timelineQuery.isPending) return <Empty description="加载中..." image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  if (!option) return <Empty description="无时间线数据" />;

  return (
    <div data-testid="timeline-chart">
      <ReactECharts option={option} style={{ height: 300 }} notMerge />
      <Space size={12} style={{ marginTop: 4 }}>
        {[
          ['llm_call', bizTokens.colorTraceLLM],
          ['tool_call', bizTokens.colorTraceTool],
          ['其他', bizTokens.colorTraceOther],
        ].map(([label, color]) => (
          <Typography.Text key={label} style={{ fontSize: 12 }}>
            <span
              style={{
                display: 'inline-block',
                width: 10,
                height: 10,
                background: color,
                borderRadius: 2,
                marginRight: 4,
              }}
            />
            {label}
          </Typography.Text>
        ))}
      </Space>
    </div>
  );
}

/** 树模式：antd Tree 展示 span 层级 */
interface SpanTreeNode {
  title: React.ReactNode;
  key: string;
  children?: SpanTreeNode[];
}

function SpanTree({ root }: { root: TraceSpanNode }) {
  const toNode = (span: TraceSpanNode): SpanTreeNode => ({
    key: span.id,
    title: (
      <Space size={6}>
        <Typography.Text style={{ fontSize: 13 }}>{span.name}</Typography.Text>
        {span.span_type && <Tag style={{ fontSize: 11 }}>{span.span_type}</Tag>}
        {span.status === 'error' && <Tag color="red">error</Tag>}
      </Space>
    ),
    children: (span.children ?? []).map(toNode),
  });

  return (
    <div data-testid="span-tree">
      <Tree defaultExpandAll treeData={[toNode(root)]} selectable={false} />
    </div>
  );
}
