/**
 * Dataset 列表页 — F2.1 + F2.2（DSL 导入抽屉）
 *
 * Reference: docs/phases/phase-f2-dataset-scenario.md §2.1/2.2
 */
import { useState } from 'react';
import {
  Alert,
  App,
  Button,
  Card,
  Col,
  Drawer,
  Form,
  Input,
  Modal,
  Popconfirm,
  Row,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import { DownloadOutlined, ImportOutlined, PlusOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import {
  useCreateDataset,
  useDatasets,
  useDeleteDataset,
  useImportDataset,
  useUpdateDataset,
} from '@/hooks/useDatasetScenario';
import { exportDataset, validateImport } from '@/api/endpoints/datasets';
import type { Dataset, ImportValidateResult } from '@/api/endpoints/datasets';
import { NotFoundResult, QueryBoundary } from '@/components/common';
import { ApiError } from '@/api/client';
import { bizTokens } from '@/theme/tokens';

/** Dataset version 约束：api-contract §1.2（semver） */
const SEMVER_PATTERN = /^\d+\.\d+\.\d+$/;

export default function DatasetListPage() {
  const { projId } = useParams<{ projId: string }>();
  const { message } = App.useApp();
  const navigate = useNavigate();

  const [page, setPage] = useState(1);
  const query = useDatasets(projId ?? null, page, 20);
  const createMut = useCreateDataset(projId ?? '');
  const updateMut = useUpdateDataset(projId ?? null);
  const deleteMut = useDeleteDataset(projId ?? null);
  const importMut = useImportDataset(projId ?? '');

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Dataset | null>(null);
  const [form] = Form.useForm();

  // 导入抽屉状态
  const [importOpen, setImportOpen] = useState(false);
  const [importForm] = Form.useForm();
  const [validateResult, setValidateResult] = useState<ImportValidateResult | null>(null);
  const [validating, setValidating] = useState(false);

  if (!projId) return <NotFoundResult />;

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (ds: Dataset) => {
    setEditing(ds);
    form.setFieldsValue({ name: ds.name, version: ds.version, description: ds.description ?? '' });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await updateMut.mutateAsync({ id: editing.id, body: { description: values.description } });
        message.success('Dataset 已更新');
      } else {
        await createMut.mutateAsync(values);
        message.success('Dataset 创建成功');
      }
      setModalOpen(false);
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    }
  };

  const handleExport = async (ds: Dataset) => {
    const yaml = await exportDataset(ds.id);
    const blob = new Blob([yaml], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${ds.name}-${ds.version}.yaml`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 导入流程：validate → preview → import（phase-f2 §2.2）
  const handleValidate = async () => {
    const values = await importForm.validateFields();
    setValidating(true);
    try {
      const result = await validateImport(projId, {
        name: values.name,
        version: values.version,
        format: 'yaml',
        content: values.content,
      });
      setValidateResult(result);
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    } finally {
      setValidating(false);
    }
  };

  const handleImport = async () => {
    const values = importForm.getFieldsValue();
    try {
      await importMut.mutateAsync({
        name: values.name,
        version: values.version,
        format: 'yaml',
        content: values.content,
      });
      message.success('导入成功');
      setImportOpen(false);
      setValidateResult(null);
      importForm.resetFields();
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          数据集
        </Typography.Title>
        <Space>
          <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)} data-testid="import-dataset-btn">
            DSL 导入
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} data-testid="create-dataset-btn">
            创建 Dataset
          </Button>
        </Space>
      </Space>

      <QueryBoundary query={query} isEmpty={(d) => d.items.length === 0} emptyText="暂无数据集">
        {(data) => (
          <Table
            rowKey="id"
            dataSource={data.items}
            pagination={{
              current: data.page,
              pageSize: data.page_size,
              total: data.total,
              onChange: setPage,
            }}
            columns={[
              {
                title: '名称',
                dataIndex: 'name',
                render: (name: string, ds) => (
                  <a onClick={() => navigate(`/datasets/${ds.id}/scenarios`)}>{name}</a>
                ),
              },
              {
                title: '版本',
                dataIndex: 'version',
                width: 120,
                render: (v: string, ds) => (
                  <Space>
                    <Tag color="blue">{v}</Tag>
                    {ds.is_latest && <Tag color="green">latest</Tag>}
                  </Space>
                ),
              },
              { title: '场景数', dataIndex: 'scenario_count', width: 100 },
              {
                title: '操作',
                width: 220,
                render: (_, ds) => (
                  <Space>
                    <a onClick={() => navigate(`/datasets/${ds.id}/scenarios`)}>场景</a>
                    <a onClick={() => openEdit(ds as Dataset)}>编辑</a>
                    <a onClick={() => handleExport(ds as Dataset)}>
                      <DownloadOutlined /> 导出
                    </a>
                    <Popconfirm title="确认删除该数据集？" onConfirm={() => deleteMut.mutateAsync(ds.id)}>
                      <a style={{ color: '#F5222D' }}>删除</a>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        )}
      </QueryBoundary>

      {/* 创建/编辑弹窗 */}
      <Modal
        title={editing ? '编辑 Dataset' : '创建 Dataset'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={createMut.isPending || updateMut.isPending}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如：客服 QA 集" disabled={!!editing} />
          </Form.Item>
          <Form.Item
            name="version"
            label="版本"
            rules={[
              { required: true, message: '请输入版本' },
              { pattern: SEMVER_PATTERN, message: '必须是 semver 格式（如 1.0.0）' },
            ]}
          >
            <Input placeholder="1.0.0" disabled={!!editing} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* DSL 导入抽屉（F2.2） */}
      <Drawer
        title="DSL 导入"
        width={640}
        open={importOpen}
        onClose={() => {
          setImportOpen(false);
          setValidateResult(null);
        }}
        extra={
          <Space>
            <Button onClick={handleValidate} loading={validating} data-testid="validate-dsl-btn">
              校验
            </Button>
            <Button
              type="primary"
              disabled={!validateResult?.valid}
              onClick={handleImport}
              loading={importMut.isPending}
              data-testid="confirm-import-btn"
            >
              确认导入
            </Button>
          </Space>
        }
      >
        <Form form={importForm} layout="vertical">
          <Row gutter={12}>
            <Col span={14}>
              <Form.Item name="name" label="数据集名称" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={10}>
              <Form.Item
                name="version"
                label="版本"
                rules={[{ required: true }, { pattern: SEMVER_PATTERN, message: 'semver 格式' }]}
              >
                <Input placeholder="1.0.0" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="content" label="YAML 内容" rules={[{ required: true, message: '请粘贴 DSL YAML' }]}>
            <Input.TextArea
              rows={12}
              style={{ fontFamily: bizTokens.fontFamilyCode, fontSize: 12 }}
              placeholder={'scenarios:\n- id: s1\n  title: 示例\n  input:\n    user_message: 你好'}
            />
          </Form.Item>
        </Form>

        {/* 校验结果（错误内联展示，不弹 toast — error-handling §2） */}
        {validateResult && !validateResult.valid && (
          <Alert
            type="error"
            showIcon
            message={`校验失败（${validateResult.errors.length} 个错误）`}
            description={
              <ul style={{ margin: 0, paddingLeft: 16 }}>
                {validateResult.errors.map((e, i) => (
                  <li key={i}>
                    <Typography.Text code>{e.scenario_external_id ?? e.field}</Typography.Text>{' '}
                    {e.message}
                  </li>
                ))}
              </ul>
            }
          />
        )}
        {validateResult?.valid && (
          <Card size="small">
            <Alert
              type="success"
              showIcon
              message={`校验通过：共 ${validateResult.scenario_count} 个场景`}
              style={{ marginBottom: validateResult.warnings.length ? 8 : 0 }}
            />
            {validateResult.warnings.length > 0 && (
              <Alert
                type="warning"
                message={`${validateResult.warnings.length} 个警告`}
                description={validateResult.warnings.map((w, i) => (
                  <div key={i}>{w.message}</div>
                ))}
              />
            )}
          </Card>
        )}
      </Drawer>
    </div>
  );
}
