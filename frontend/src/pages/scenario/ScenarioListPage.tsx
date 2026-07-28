/**
 * Scenario 列表页 — F2.3
 *
 * Reference: docs/phases/phase-f2-dataset-scenario.md §2.3
 * 关键约束：字段名 input/expected（api-contract §1.2）；分页入 searchParams
 */
import { useState } from 'react';
import {
  App,
  Button,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useParams, useSearchParams } from 'react-router-dom';
import {
  useBatchCreateScenarios,
  useDataset,
  useDeleteScenario,
  useScenario,
  useScenarios,
  useUpdateScenario,
} from '@/hooks/useDatasetScenario';
import { NotFoundResult, QueryBoundary } from '@/components/common';
import { ApiError } from '@/api/client';
import { formatJson, parseJsonObject } from '@/utils/json';
import { bizTokens } from '@/theme/tokens';

const jsonAreaStyle = { fontFamily: bizTokens.fontFamilyCode, fontSize: 12 };

/** JSON 对象表单校验规则（AC-F2-03） */
const jsonObjectRule = {
  validator: (_: unknown, value: string) =>
    !value || parseJsonObject(value)
      ? Promise.resolve()
      : Promise.reject(new Error('必须是合法 JSON 对象')),
};

export default function ScenarioListPage() {
  const { dsId } = useParams<{ dsId: string }>();
  const { message } = App.useApp();
  // 分页参数入 searchParams（design-principles P4）
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get('page') ?? 1);

  const dsQuery = useDataset(dsId ?? null);
  const query = useScenarios(dsId ?? null, page, 20);
  const batchMut = useBatchCreateScenarios(dsId ?? '');
  const updateMut = useUpdateScenario(dsId ?? null);
  const deleteMut = useDeleteScenario(dsId ?? null);

  // 批量创建弹窗
  const [batchOpen, setBatchOpen] = useState(false);
  const [batchForm] = Form.useForm();

  // 编辑抽屉
  const [editingId, setEditingId] = useState<string | null>(null);
  const detailQuery = useScenario(editingId);

  if (!dsId) return <NotFoundResult />;

  const handleBatchSubmit = async () => {
    const values = await batchForm.validateFields();
    const rows = (values.rows ?? []).filter((r: { external_id?: string }) => r?.external_id);
    if (rows.length === 0) {
      message.warning('至少添加一行场景');
      return;
    }
    try {
      await batchMut.mutateAsync(
        rows.map((r: { external_id: string; title: string; query: string; expected_contains?: string }) => ({
          external_id: r.external_id,
          title: r.title,
          // 键名必须是 user_message（Runner 读 input_data["user_message"]，api-contract §1.2）
          input: { user_message: r.query },
          // expected 模板：response_contains 是 Rule Judge 生效的关键字段（phase-f2 §3）
          expected: r.expected_contains
            ? { response_contains: r.expected_contains.split(',').map((s) => s.trim()).filter(Boolean) }
            : undefined,
        })),
      );
      message.success(`成功创建 ${rows.length} 个场景`);
      setBatchOpen(false);
      batchForm.resetFields();
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    }
  };

  const openEdit = (id: string) => {
    setEditingId(id);
  };

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          {dsQuery.data ? `${dsQuery.data.name} v${dsQuery.data.version} / 场景` : '场景'}
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setBatchOpen(true)} data-testid="batch-create-btn">
          批量创建
        </Button>
      </Space>

      <QueryBoundary query={query} isEmpty={(d) => d.items.length === 0} emptyText="暂无场景，点击右上角批量创建">
        {(data) => (
          <Table
            rowKey="id"
            dataSource={data.items}
            pagination={{
              current: data.page,
              pageSize: data.page_size,
              total: data.total,
              onChange: (p) => setSearchParams({ page: String(p) }),
              showTotal: (t) => `共 ${t} 个场景`,
            }}
            columns={[
              { title: 'ID', dataIndex: 'external_id', width: 140 },
              {
                title: '标题',
                dataIndex: 'title',
                render: (t: string, s) => <a onClick={() => openEdit(s.id)}>{t}</a>,
              },
              {
                title: '标签',
                dataIndex: 'tags',
                render: (tags: string[]) => tags?.map((t) => <Tag key={t}>{t}</Tag>),
              },
              { title: '状态', dataIndex: 'status', width: 90 },
              { title: '优先级', dataIndex: 'priority', width: 80 },
              {
                title: '操作',
                width: 140,
                render: (_, s) => (
                  <Space>
                    <a onClick={() => openEdit(s.id)}>编辑</a>
                    <Popconfirm title="确认删除该场景？" onConfirm={() => deleteMut.mutateAsync(s.id)}>
                      <a style={{ color: '#F5222D' }}>删除</a>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        )}
      </QueryBoundary>

      {/* 批量创建弹窗 */}
      <Modal
        title="批量创建场景"
        width={800}
        open={batchOpen}
        onOk={handleBatchSubmit}
        onCancel={() => setBatchOpen(false)}
        confirmLoading={batchMut.isPending}
        destroyOnHidden
      >
        <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
          期望包含：逗号分隔的关键词，将写入 expected.response_contains（Rule Judge 依据此评分）
        </Typography.Paragraph>
        <Form form={batchForm} autoComplete="off">
          <Form.List name="rows" initialValue={[{}]}>
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Space key={field.key} align="baseline" style={{ display: 'flex', marginBottom: 4 }}>
                    <Form.Item
                      name={[field.name, 'external_id']}
                      rules={[{ required: true, message: '必填' }]}
                    >
                      <Input placeholder="ID（如 s1）" style={{ width: 110 }} />
                    </Form.Item>
                    <Form.Item name={[field.name, 'title']} rules={[{ required: true, message: '必填' }]}>
                      <Input placeholder="标题" style={{ width: 150 }} />
                    </Form.Item>
                    <Form.Item name={[field.name, 'query']} rules={[{ required: true, message: '必填' }]}>
                      <Input placeholder="用户问题（input.user_message）" style={{ width: 220 }} />
                    </Form.Item>
                    <Form.Item name={[field.name, 'expected_contains']}>
                      <Input placeholder="期望包含（逗号分隔）" style={{ width: 180 }} />
                    </Form.Item>
                    <a onClick={() => remove(field.name)}>删除</a>
                  </Space>
                ))}
                <Button block type="dashed" onClick={() => add()}>
                  + 添加一行
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>

      {/* 编辑抽屉（JSON 编辑 input/expected） */}
      <Drawer
        title={`编辑场景 ${detailQuery.data?.external_id ?? ''}`}
        width={560}
        open={!!editingId}
        onClose={() => setEditingId(null)}
        destroyOnHidden
      >
        <QueryBoundary query={detailQuery}>
          {(scenario) => (
            <ScenarioEditForm
              // 数据版本变化时强制重新挂载，保证初始值与最新详情一致
              key={`${scenario.id}-${scenario.updated_at ?? ''}`}
              scenario={scenario}
              saving={updateMut.isPending}
              onSave={async (body) => {
                try {
                  await updateMut.mutateAsync({ id: scenario.id, body });
                  message.success('场景已更新');
                  setEditingId(null);
                } catch (e) {
                  if (e instanceof ApiError) message.error(e.message);
                  else throw e;
                }
              }}
            />
          )}
        </QueryBoundary>
      </Drawer>
    </div>
  );
}

/** 编辑表单子组件：自持 form 实例，随 key 重建，避免复用 store 残留旧值 */
function ScenarioEditForm({
  scenario,
  saving,
  onSave,
}: {
  scenario: import('@/api/endpoints/datasets').Scenario;
  saving: boolean;
  onSave: (body: {
    title: string;
    input: Record<string, unknown>;
    expected: Record<string, unknown>;
    priority?: number;
  }) => Promise<void>;
}) {
  const [form] = Form.useForm();

  const handleSubmit = async () => {
    const values = await form.validateFields();
    const input = parseJsonObject(values.input);
    const expected = values.expected ? parseJsonObject(values.expected) : {};
    if (!input) return; // jsonObjectRule 已拦截，此处兼容兼防
    await onSave({ title: values.title, input, expected: expected ?? {}, priority: values.priority });
  };

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={{
        title: scenario.title,
        input: formatJson(scenario.input),
        expected: formatJson(scenario.expected),
        priority: scenario.priority,
      }}
    >
      <Form.Item name="title" label="标题" rules={[{ required: true }]}>
        <Input />
      </Form.Item>
      <Form.Item
        name="input"
        label="Input（JSON）"
        rules={[{ required: true, message: '必填' }, jsonObjectRule]}
        tooltip='Agent 输入，如 {"user_message": "..."}（键名必须是 user_message）'
      >
        <Input.TextArea rows={6} style={jsonAreaStyle} data-testid="input-json" />
      </Form.Item>
      <Form.Item
        name="expected"
        label="Expected（JSON）"
        rules={[jsonObjectRule]}
        tooltip='评分期望，response_contains 数组是 Rule Judge 生效的关键字段'
      >
        <Input.TextArea rows={6} style={jsonAreaStyle} data-testid="expected-json" />
      </Form.Item>
      <Form.Item name="priority" label="优先级">
        <InputNumber min={0} max={10} />
      </Form.Item>
      <Button type="primary" block onClick={handleSubmit} loading={saving} data-testid="save-scenario-btn">
        保存
      </Button>
    </Form>
  );
}
