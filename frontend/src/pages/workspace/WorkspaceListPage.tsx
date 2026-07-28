/**
 * Workspace 列表页 — F1.5
 *
 * Reference: docs/phases/phase-f1-foundation.md §4
 */
import { useState } from 'react';
import { App, Button, Form, Input, Modal, Popconfirm, Space, Table, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  useCreateWorkspace,
  useDeleteWorkspace,
  useUpdateWorkspace,
  useWorkspaces,
} from '@/hooks/useWorkspaceProject';
import { useContextStore } from '@/stores/contextStore';
import { QueryBoundary } from '@/components/common';
import { ApiError } from '@/api/client';
import { SLUG_PATTERN, toSlug } from '@/utils/slug';
import type { Workspace } from '@/api/types';

export default function WorkspaceListPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const setWorkspace = useContextStore((s) => s.setWorkspace);

  const [page, setPage] = useState(1);
  const query = useWorkspaces(page, 20);
  const createMut = useCreateWorkspace();
  const updateMut = useUpdateWorkspace();
  const deleteMut = useDeleteWorkspace();

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Workspace | null>(null);
  const [form] = Form.useForm();

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (ws: Workspace) => {
    setEditing(ws);
    form.setFieldsValue({ name: ws.name, slug: ws.slug, description: ws.description ?? '' });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await updateMut.mutateAsync({ id: editing.id, body: values });
        message.success('Workspace 已更新');
      } else {
        await createMut.mutateAsync(values);
        message.success('Workspace 创建成功');
      }
      setModalOpen(false);
    } catch (e) {
      // 409 冲突等业务错误：message 展示后端原文（error-handling §2）
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    }
  };

  const handleDelete = async (id: string) => {
    await deleteMut.mutateAsync(id);
    message.success('已删除');
  };

  const enterWorkspace = (ws: Workspace) => {
    setWorkspace(ws.id);
    navigate(`/workspaces/${ws.id}/projects`);
  };

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          Workspaces
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} data-testid="create-workspace-btn">
          创建 Workspace
        </Button>
      </Space>

      <QueryBoundary query={query} isEmpty={(d) => d.items.length === 0} emptyText="还没有 Workspace，点击右上角创建">
        {(data) => (
          <Table
            rowKey="id"
            dataSource={data.items}
            pagination={{
              current: data.page,
              pageSize: data.page_size,
              total: data.total,
              onChange: setPage,
              showTotal: (t) => `共 ${t} 个`,
            }}
            columns={[
              {
                title: '名称',
                dataIndex: 'name',
                render: (name: string, ws) => <a onClick={() => enterWorkspace(ws)}>{name}</a>,
              },
              { title: 'Slug', dataIndex: 'slug' },
              { title: '项目数', dataIndex: 'project_count', width: 100 },
              {
                title: '操作',
                width: 180,
                render: (_, ws) => (
                  <Space>
                    <a onClick={() => openEdit(ws)}>编辑</a>
                    <Popconfirm
                      title="确认删除该 Workspace？"
                      description="删除后其下项目不可访问"
                      onConfirm={() => handleDelete(ws.id)}
                    >
                      <a style={{ color: '#F5222D' }}>删除</a>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        )}
      </QueryBoundary>

      <Modal
        title={editing ? '编辑 Workspace' : '创建 Workspace'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={createMut.isPending || updateMut.isPending}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          onValuesChange={(changed) => {
            // slug 从 name 自动生成（仅创建时）
            if (!editing && changed.name !== undefined) {
              form.setFieldValue('slug', toSlug(changed.name));
            }
          }}
        >
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如：搜索团队" />
          </Form.Item>
          <Form.Item
            name="slug"
            label="Slug"
            rules={[
              { required: true, message: '请输入 slug' },
              { pattern: SLUG_PATTERN, message: '仅允许小写字母、数字、连字符' },
            ]}
          >
            <Input placeholder="如：search-team" disabled={!!editing} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
