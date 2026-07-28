/**
 * AppLayout — 侧边栏 + 顶栏 + 上下文选择器 + 面包屑出口
 *
 * Reference: docs/contracts/route-map.md §2
 */
import { useState } from 'react';
import { Layout, Menu, Select, Space, Typography } from 'antd';
import {
  AppstoreOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  DiffOutlined,
  ApiOutlined,
  HomeOutlined,
} from '@ant-design/icons';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useContextStore } from '@/stores/contextStore';
import { useProjects, useWorkspace, useWorkspaces } from '@/hooks/useWorkspaceProject';
import { bizTokens } from '@/theme/tokens';

const { Sider, Header, Content } = Layout;

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { workspaceId, projectId, setWorkspace, setProject } = useContextStore();

  // Workspace 选择器走服务端 search（数据量可能远超单页上限，实测 132 条）
  const [wsSearch, setWsSearch] = useState('');
  const workspacesQuery = useWorkspaces(1, 50, wsSearch || undefined);
  const projectsQuery = useProjects(workspaceId, 1, 100);

  // 当前选中项可能不在搜索结果内 → 单独取详情补进选项，避免显示为空
  const selectedWorkspace = useWorkspace(workspaceId);

  const wsItems = workspacesQuery.data?.items ?? [];
  const workspaceOptions = [
    ...wsItems.map((w) => ({ value: w.id, label: w.name })),
    ...(selectedWorkspace.data && !wsItems.some((w) => w.id === selectedWorkspace.data!.id)
      ? [{ value: selectedWorkspace.data.id, label: selectedWorkspace.data.name }]
      : []),
  ];
  const projectOptions = (projectsQuery.data?.items ?? []).map((p) => ({
    value: p.id,
    label: p.name,
  }));

  // 侧边栏菜单：全局项 + 选中 project 后的项目级菜单
  const menuItems = [
    { key: '/workspaces', icon: <HomeOutlined />, label: 'Workspaces' },
    ...(projectId
      ? [
          {
            key: `/projects/${projectId}`,
            icon: <AppstoreOutlined />,
            label: '项目概览',
          },
          {
            key: `/projects/${projectId}/datasets`,
            icon: <DatabaseOutlined />,
            label: '数据集',
          },
          {
            key: `/projects/${projectId}/evaluations`,
            icon: <ExperimentOutlined />,
            label: '评测',
          },
          {
            key: `/projects/${projectId}/regressions`,
            icon: <DiffOutlined />,
            label: '回归对比',
          },
        ]
      : []),
    { key: '/plugins', icon: <ApiOutlined />, label: '插件管理' },
  ];

  const selectedKey =
    menuItems
      .map((i) => i.key)
      .filter((k) => location.pathname === k || location.pathname.startsWith(k + '/'))
      .sort((a, b) => b.length - a.length)[0] ?? '/workspaces';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={bizTokens.siderWidth} theme="dark">
        <div
          style={{
            height: bizTokens.headerHeight,
            display: 'flex',
            alignItems: 'center',
            paddingLeft: 20,
          }}
        >
          <Typography.Text strong style={{ color: '#fff', fontSize: 16 }}>
            AgentEval
          </Typography.Text>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            height: bizTokens.headerHeight,
            lineHeight: `${bizTokens.headerHeight}px`,
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <Space>
            <Select
              data-testid="workspace-selector"
              style={{ width: 200 }}
              placeholder="选择 Workspace"
              options={workspaceOptions}
              value={workspaceId ?? undefined}
              onChange={(id) => {
                setWorkspace(id);
                navigate(`/workspaces/${id}/projects`);
              }}
              showSearch
              // 服务端搜索：过滤交给后端，禁用本地过滤
              filterOption={false}
              onSearch={setWsSearch}
              loading={workspacesQuery.isFetching}
              notFoundContent={workspacesQuery.isFetching ? '搜索中...' : '无匹配'}
            />
            <Select
              data-testid="project-selector"
              style={{ width: 200 }}
              placeholder="选择 Project"
              options={projectOptions}
              value={projectId ?? undefined}
              disabled={!workspaceId}
              onChange={(id) => {
                setProject(id);
                navigate(`/projects/${id}`);
              }}
              showSearch
              optionFilterProp="label"
            />
          </Space>
        </Header>
        <Content style={{ padding: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
