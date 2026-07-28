/**
 * Evaluation 列表页 — F3.2
 *
 * Reference: docs/phases/phase-f3-evaluation.md §2.2
 * 列表行不展示精确进度/pass_rate（api-contract §1.4，禁止 N+1）
 */
import { App, Button, Popconfirm, Space, Table, Tabs, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useCancelEvaluation, useEvaluations } from '@/hooks/useEvaluations';
import { NotFoundResult, QueryBoundary, StatusTag } from '@/components/common';
import { ApiError } from '@/api/client';

const STATUS_TABS = [
  { key: 'all', label: '全部' },
  { key: 'running', label: '执行中' },
  { key: 'completed', label: '已完成' },
  { key: 'failed', label: '失败' },
];

export default function EvaluationListPage() {
  const { projId } = useParams<{ projId: string }>();
  const { message } = App.useApp();
  const navigate = useNavigate();
  // status 筛选与分页入 searchParams（design-principles P4）
  const [searchParams, setSearchParams] = useSearchParams();
  const statusFilter = searchParams.get('status') ?? 'all';
  const page = Number(searchParams.get('page') ?? 1);

  const query = useEvaluations(projId ?? null, page, statusFilter === 'all' ? undefined : statusFilter);
  const cancelMut = useCancelEvaluation();

  if (!projId) return <NotFoundResult />;

  const handleCancel = async (id: string) => {
    try {
      await cancelMut.mutateAsync(id);
      message.success('评测已取消');
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 8, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          评测
        </Typography.Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate(`/projects/${projId}/evaluations/new`)}
          data-testid="create-evaluation-btn"
        >
          发起评测
        </Button>
      </Space>

      <Tabs
        activeKey={statusFilter}
        items={STATUS_TABS}
        onChange={(key) => setSearchParams(key === 'all' ? {} : { status: key })}
      />

      <QueryBoundary query={query} isEmpty={(d) => d.items.length === 0} emptyText="暂无评测">
        {(data) => (
          <Table
            rowKey="id"
            dataSource={data.items}
            pagination={{
              current: data.page,
              pageSize: data.page_size,
              total: data.total,
              onChange: (p) =>
                setSearchParams(
                  statusFilter === 'all' ? { page: String(p) } : { status: statusFilter, page: String(p) },
                ),
            }}
            columns={[
              {
                title: '名称',
                dataIndex: 'name',
                render: (name: string, e) => (
                  <a onClick={() => navigate(`/evaluations/${e.id}`)}>{name}</a>
                ),
              },
              {
                title: '版本',
                dataIndex: 'version_label',
                width: 100,
                render: (v: string | null) => v ?? '-',
              },
              {
                title: '状态',
                dataIndex: 'status',
                width: 110,
                render: (s: string) => <StatusTag status={s} />,
              },
              {
                title: '创建时间',
                dataIndex: 'created_at',
                width: 180,
                render: (t: string) => new Date(t).toLocaleString(),
              },
              {
                title: '操作',
                width: 140,
                render: (_, e) => (
                  <Space>
                    <a onClick={() => navigate(`/evaluations/${e.id}`)}>查看</a>
                    {['pending', 'running'].includes(e.status) && (
                      <Popconfirm title="确认取消该评测？" onConfirm={() => handleCancel(e.id)}>
                        <a style={{ color: '#F5222D' }}>取消</a>
                      </Popconfirm>
                    )}
                  </Space>
                ),
              },
            ]}
          />
        )}
      </QueryBoundary>
    </div>
  );
}
