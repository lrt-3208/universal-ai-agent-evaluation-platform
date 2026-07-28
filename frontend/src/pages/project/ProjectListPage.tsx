/**
 * Project 列表页 — F1.5
 *
 * Reference: docs/phases/phase-f1-foundation.md §4
 * Project 创建必填 agent_config（adapter_type + endpoint，endpoint 不带 /chat）
 */
import { useState } from 'react';
import { App, Button, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useCreateProject, useDeleteProject, useProjects, useWorkspace } from '@/hooks/useWorkspaceProject';
import { useContextStore } from '@/stores/contextStore';
import { NotFoundResult, QueryBoundary } from '@/components/common';
import { ApiError } from '@/api/client';
import { SLUG_PATTERN, toSlug } from '@/utils/slug';
import type { Project } from '@/api/types';

export default function ProjectListPage() {
  const { wsId } = useParams<{ wsId: string }>();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const setProject = useContextStore((s) => s.setProject);

  const wsQuery = useWorkspace(wsId ?? null);
  const [page, setPage] = useState(1);
  const query = useProjects(wsId ?? null, page, 20);
  const createMut = useCreateProject(wsId ?? '');
  const deleteMut = useDeleteProject(wsId ?? null);

  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  if (!wsId) return <NotFoundResult />;

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      await createMut.mutateAsync({
        name: values.name,
        slug: values.slug,
        description: values.description,
        agent_config: {
          adapter_type: values.adapter_type,
          endpoint: values.endpoint,
        },
      });
      message.success('Project 创建成功');
      setModalOpen(false);
      form.resetFields();
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    }
  };

  const enterProject = (p: Project) => {
    setProject(p.id);
    navigate(`/projects/${p.id}`);
  };

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          {wsQuery.data ? `${wsQuery.data.name} / 项目` : '项目'}
        </Typography.Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setModalOpen(true)}
          data-testid="create-project-btn"
        >
          创建 Project
        </Button>
      </Space>

      <QueryBoundary query={query} isEmpty={(d) => d.items.length === 0} emptyText="该 Workspace 下暂无项目">
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
                render: (name: string, p) => <a onClick={() => enterProject(p)}>{name}</a>,
              },
              { title: 'Slug', dataIndex: 'slug' },
              {
                title: 'Adapter',
                render: (_, p) => <Tag>{p.agent_config?.adapter_type ?? '-'}</Tag>,
                width: 120,
              },
              {
                title: '操作',
                width: 120,
                render: (_, p) => (
                  <Popconfirm title="确认删除该项目？" onConfirm={() => deleteMut.mutateAsync(p.id)}>
                    <a style={{ color: '#F5222D' }}>删除</a>
                  </Popconfirm>
                ),
              },
            ]}
          />
        )}
      </QueryBoundary>

      <Modal
        title="创建 Project"
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={createMut.isPending}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ adapter_type: 'http' }}
          onValuesChange={(changed) => {
            if (changed.name !== undefined) form.setFieldValue('slug', toSlug(changed.name));
          }}
        >
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如：客服机器人" />
          </Form.Item>
          <Form.Item
            name="slug"
            label="Slug"
            rules={[
              { required: true, message: '请输入 slug' },
              { pattern: SLUG_PATTERN, message: '仅允许小写字母、数字、连字符' },
            ]}
          >
            <Input placeholder="如：cs-bot" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item
            name="adapter_type"
            label="Adapter 类型"
            rules={[{ required: true }]}
            tooltip="被测 Agent 的接入方式"
          >
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
            label="Agent Endpoint"
            rules={[{ required: true, message: '请输入 endpoint' }]}
            tooltip="Agent base URL，不带 /chat（HTTP Adapter 会自动拼接）"
          >
            <Input placeholder="http://localhost:9001" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
