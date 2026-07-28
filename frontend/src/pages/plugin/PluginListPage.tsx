/**
 * 插件管理页 — F7.2
 *
 * Reference: docs/phases/phase-f7-plugin.md §2
 */
import { useState } from 'react';
import {
  Alert,
  App,
  Button,
  Card,
  Col,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  Row,
  Space,
  Switch,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { ReloadOutlined, SettingOutlined, SyncOutlined } from '@ant-design/icons';
import {
  useDiscoverPlugins,
  usePluginAction,
  usePlugins,
  useUpdatePluginConfig,
} from '@/hooks/usePlugins';
import type { Plugin } from '@/api/endpoints/plugins';
import { QueryBoundary, StatusTag } from '@/components/common';
import { formatJson, parseJsonObject } from '@/utils/json';
import { bizTokens } from '@/theme/tokens';
import { ApiError } from '@/api/client';

const TYPE_TABS = [
  { key: 'all', label: '全部' },
  { key: 'judge', label: 'Judge' },
  { key: 'adapter', label: 'Adapter' },
  { key: 'dataset', label: 'Dataset' },
  { key: 'metrics', label: 'Metrics' },
  { key: 'report', label: 'Report' },
];

export default function PluginListPage() {
  const { message } = App.useApp();
  const [typeFilter, setTypeFilter] = useState('all');
  const query = usePlugins(typeFilter === 'all' ? undefined : typeFilter);
  const discoverMut = useDiscoverPlugins();
  const actionMut = usePluginAction();
  const [configPlugin, setConfigPlugin] = useState<Plugin | null>(null);

  const handleDiscover = async () => {
    const items = await discoverMut.mutateAsync();
    message.success(`扫描完成，共发现 ${items.length} 个插件`);
  };

  const handleAction = async (name: string, action: 'enable' | 'disable' | 'reload') => {
    try {
      const result = await actionMut.mutateAsync({ name, action });
      message.success(result.message);
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 8, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          插件管理
        </Typography.Title>
        <Button
          icon={<SyncOutlined />}
          onClick={handleDiscover}
          loading={discoverMut.isPending}
          data-testid="discover-plugins-btn"
        >
          重新扫描
        </Button>
      </Space>

      <Tabs activeKey={typeFilter} items={TYPE_TABS} onChange={setTypeFilter} />

      <QueryBoundary query={query} isEmpty={(d) => d.length === 0} emptyText="暂无插件，点击右上角扫描插件目录">
        {(plugins) => (
          <Row gutter={[16, 16]}>
            {plugins.map((p) => (
              <Col key={p.id} span={8}>
                <PluginCard
                  plugin={p}
                  onAction={handleAction}
                  onConfig={() => setConfigPlugin(p)}
                  actionPending={actionMut.isPending}
                />
              </Col>
            ))}
          </Row>
        )}
      </QueryBoundary>

      <PluginConfigDrawer plugin={configPlugin} onClose={() => setConfigPlugin(null)} />
    </div>
  );
}

function PluginCard({
  plugin,
  onAction,
  onConfig,
  actionPending,
}: {
  plugin: Plugin;
  onAction: (name: string, action: 'enable' | 'disable' | 'reload') => void;
  onConfig: () => void;
  actionPending: boolean;
}) {
  return (
    <Card
      size="small"
      data-testid={`plugin-card-${plugin.name}`}
      title={
        <Space>
          <Typography.Text strong>{plugin.name}</Typography.Text>
          <Tag>{plugin.type}</Tag>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            v{plugin.version}
          </Typography.Text>
        </Space>
      }
      extra={<StatusTag status={plugin.status} />}
      actions={[
        plugin.status === 'enabled' ? (
          <Button
            key="disable"
            type="text"
            size="small"
            disabled={actionPending}
            onClick={() => onAction(plugin.name, 'disable')}
            data-testid={`disable-${plugin.name}`}
          >
            禁用
          </Button>
        ) : (
          <Button
            key="enable"
            type="text"
            size="small"
            disabled={actionPending}
            onClick={() => onAction(plugin.name, 'enable')}
            data-testid={`enable-${plugin.name}`}
          >
            启用
          </Button>
        ),
        <Button
          key="reload"
          type="text"
          size="small"
          icon={<ReloadOutlined />}
          disabled={plugin.status !== 'enabled' || actionPending}
          onClick={() => onAction(plugin.name, 'reload')}
          data-testid={`reload-${plugin.name}`}
        >
          重载
        </Button>,
        <Button
          key="config"
          type="text"
          size="small"
          icon={<SettingOutlined />}
          onClick={onConfig}
          data-testid={`config-${plugin.name}`}
        >
          配置
        </Button>,
      ]}
    >
      <Typography.Paragraph type="secondary" style={{ fontSize: 12, minHeight: 36 }} ellipsis={{ rows: 2 }}>
        {plugin.description ?? '-'}
      </Typography.Paragraph>
      <Typography.Text type="secondary" style={{ fontSize: 11 }}>
        {plugin.author ?? ''}
      </Typography.Text>
      {plugin.status === 'error' && plugin.error_message && (
        <Alert type="error" message={plugin.error_message} style={{ marginTop: 8 }} />
      )}
    </Card>
  );
}

/**
 * 配置抽屉：按 JSON Schema properties 渲染表单
 * 仅支持 string/number/boolean，复杂结构降级 JSON 编辑器（phase-f7 §2.2）
 */
function PluginConfigDrawer({ plugin, onClose }: { plugin: Plugin | null; onClose: () => void }) {
  const { message } = App.useApp();
  const updateMut = useUpdatePluginConfig();

  if (!plugin) return <Drawer open={false} onClose={onClose} />;

  const properties = plugin.config_schema?.properties ?? {};
  const simpleTypes = ['string', 'number', 'boolean'];
  const isSimple =
    Object.keys(properties).length > 0 &&
    Object.values(properties).every((p) => simpleTypes.includes(p.type ?? ''));

  return (
    <Drawer
      title={`配置 ${plugin.name}`}
      open
      onClose={onClose}
      width={480}
      destroyOnHidden
    >
      <ConfigForm
        key={plugin.id}
        plugin={plugin}
        isSimple={isSimple}
        onSave={async (config) => {
          try {
            await updateMut.mutateAsync({ name: plugin.name, config });
            message.success(
              plugin.status === 'enabled' ? '配置已保存，需重载生效' : '配置已保存',
            );
            onClose();
          } catch (e) {
            if (e instanceof ApiError) message.error(e.message);
            else throw e;
          }
        }}
        saving={updateMut.isPending}
      />
    </Drawer>
  );
}

function ConfigForm({
  plugin,
  isSimple,
  onSave,
  saving,
}: {
  plugin: Plugin;
  isSimple: boolean;
  onSave: (config: Record<string, unknown>) => Promise<void>;
  saving: boolean;
}) {
  const [form] = Form.useForm();
  const properties = plugin.config_schema?.properties ?? {};

  const handleSubmit = async () => {
    const values = await form.validateFields();
    if (isSimple) {
      await onSave(values);
    } else {
      const parsed = parseJsonObject(values.raw);
      if (!parsed) return;
      await onSave(parsed);
    }
  };

  if (!isSimple) {
    // 复杂/空 schema 降级为 JSON 编辑器
    return (
      <Form form={form} layout="vertical" initialValues={{ raw: formatJson(plugin.config) }}>
        <Form.Item
          name="raw"
          label="配置（JSON）"
          rules={[
            {
              validator: (_, v: string) =>
                parseJsonObject(v) ? Promise.resolve() : Promise.reject(new Error('必须是合法 JSON 对象')),
            },
          ]}
        >
          <Input.TextArea rows={10} style={{ fontFamily: bizTokens.fontFamilyCode, fontSize: 12 }} />
        </Form.Item>
        <Button type="primary" block onClick={handleSubmit} loading={saving} data-testid="save-plugin-config-btn">
          保存
        </Button>
      </Form>
    );
  }

  if (Object.keys(properties).length === 0) {
    return <Empty description="该插件无可配置项" />;
  }

  return (
    <Form form={form} layout="vertical" initialValues={plugin.config}>
      {Object.entries(properties).map(([key, prop]) => (
        <Form.Item
          key={key}
          name={key}
          label={key}
          valuePropName={prop.type === 'boolean' ? 'checked' : 'value'}
          initialValue={plugin.config[key] ?? prop.default}
        >
          {prop.type === 'number' ? (
            <InputNumber
              style={{ width: '100%' }}
              min={prop.minimum}
              max={prop.maximum}
              data-testid={`config-field-${key}`}
            />
          ) : prop.type === 'boolean' ? (
            <Switch data-testid={`config-field-${key}`} />
          ) : (
            <Input data-testid={`config-field-${key}`} />
          )}
        </Form.Item>
      ))}
      <Button type="primary" block onClick={handleSubmit} loading={saving} data-testid="save-plugin-config-btn">
        保存
      </Button>
    </Form>
  );
}
