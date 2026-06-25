import { useState, useEffect, useCallback } from 'react';
import { PageContainer } from '@ant-design/pro-components';
import {
  Card,
  Tabs,
  Form,
  Input,
  Button,
  Space,
  Switch,
  App,
  Tag,
  Table,
  Popconfirm,
  Descriptions,
  Alert,
  Typography,
  Spin,
} from 'antd';
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DisconnectOutlined,
  TeamOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import {
  integrationApi,
  type IntegrationProvider,
  type IntegrationConfig,
  type IntegrationProviderInfo,
  type IntegrationBinding,
} from '@hospital/api';
import { useAccess } from '@umijs/max';

const { Text } = Typography;

// 各平台表单字段差异配置
const PROVIDER_FORM_META: Record<
  IntegrationProvider,
  {
    label: string;
    appIdLabel: string;
    appIdPlaceholder: string;
    secretEnvHint: string;
    needsAgentId: boolean;
    webhookHelp: string;
  }
> = {
  dingtalk: {
    label: '钉钉',
    appIdLabel: 'AppKey',
    appIdPlaceholder: '钉钉应用 AppKey',
    secretEnvHint: '环境变量名，如 DINGTALK_APP_SECRET（数据库仅存 env: 引用）',
    needsAgentId: true,
    webhookHelp: '钉钉群机器人「安全设置-加签」里的 Webhook 地址',
  },
  wecom: {
    label: '企业微信',
    appIdLabel: 'CorpID',
    appIdPlaceholder: '企业微信企业ID',
    secretEnvHint: '环境变量名，如 WECOM_APP_SECRET',
    needsAgentId: true,
    webhookHelp: '企业微信群机器人 Webhook 地址（key 参数可留空，已在 URL 中）',
  },
  feishu: {
    label: '飞书',
    appIdLabel: 'App ID',
    appIdPlaceholder: '飞书自建应用 App ID',
    secretEnvHint: '环境变量名，如 FEISHU_APP_SECRET',
    needsAgentId: false,
    webhookHelp: '飞书自定义机器人 Webhook 地址（启用签名校验时填密钥变量名）',
  },
};

function ProviderConfigTab({
  provider,
  providerInfo,
  onSaved,
}: {
  provider: IntegrationProvider;
  providerInfo?: IntegrationProviderInfo;
  onSaved: () => void;
}) {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [config, setConfig] = useState<IntegrationConfig | null>(null);
  const [bindings, setBindings] = useState<IntegrationBinding[]>([]);
  const meta = PROVIDER_FORM_META[provider];

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [cfg, bds] = await Promise.all([
        integrationApi.get(provider).catch(() => null),
        integrationApi.listBindings(provider).catch(() => []),
      ]);
      setConfig(cfg);
      setBindings(bds);
      if (cfg) {
        form.setFieldsValue({
          name: cfg.name,
          app_id: cfg.app_id,
          app_secret_ref: '',
          webhook_url: cfg.webhook_url,
          webhook_secret_ref: '',
          agent_id: (cfg.extra_config as Record<string, unknown> | null)?.agent_id ?? '',
          status: cfg.status === 1,
        });
      } else {
        form.setFieldsValue({ name: meta.label, status: true });
      }
    } finally {
      setLoading(false);
    }
  }, [provider, form, meta.label]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const extra_config: Record<string, unknown> = {};
      if (meta.needsAgentId && values.agent_id) {
        extra_config.agent_id = values.agent_id;
      }
      await integrationApi.upsert({
        provider,
        name: values.name || meta.label,
        app_id: values.app_id || null,
        // 仅在用户填写了新值时才更新 secret 引用（避免覆盖已存配置）
        app_secret_ref: values.app_secret_ref ? `env:${values.app_secret_ref}` : null,
        webhook_url: values.webhook_url || null,
        webhook_secret_ref: values.webhook_secret_ref
          ? `env:${values.webhook_secret_ref}`
          : null,
        extra_config: Object.keys(extra_config).length ? extra_config : null,
        status: values.status ? 1 : 0,
      });
      message.success(`${meta.label} 配置保存成功`);
      onSaved();
      load();
    } catch (e) {
      if ((e as Error)?.message) {
        message.error(`保存失败: ${(e as Error).message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      const result = await integrationApi.testConnection(provider);
      if (result.success) {
        message.success(result.message);
      } else {
        message.error(result.message);
      }
    } catch (e) {
      message.error(`测试失败: ${(e as Error).message}`);
    } finally {
      setTesting(false);
    }
  };

  const handleSync = async () => {
    try {
      const result = await integrationApi.syncOrganization(provider);
      message.success(`${result.message}（任务ID: ${result.task_id.slice(0, 8)}...）`);
    } catch (e) {
      message.error(`同步触发失败: ${(e as Error).message}`);
    }
  };

  const handleDelete = async () => {
    try {
      await integrationApi.remove(provider);
      message.success('已删除配置');
      form.resetFields();
      onSaved();
      load();
    } catch (e) {
      message.error(`删除失败: ${(e as Error).message}`);
    }
  };

  const handleUnbind = async (bindingId: string) => {
    try {
      await integrationApi.removeBinding(provider, bindingId);
      message.success('已解绑');
      setBindings((prev) => prev.filter((b) => b.id !== bindingId));
    } catch (e) {
      message.error(`解绑失败: ${(e as Error).message}`);
    }
  };

  const configured = !!config;
  const enabled = config?.status === 1;

  return (
    <Spin spinning={loading}>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Alert
          type="info"
          showIcon
          message={`${meta.label} 集成说明`}
          description={
            <ul style={{ marginBottom: 0, paddingLeft: 18 }}>
              <li>
                <Text strong>凭证安全</Text>：AppID 可直接保存；App Secret
                <Text code> 仅填写环境变量名</Text>（如 DINGTALK_APP_SECRET），数据库只存
                <Text code> env:变量名</Text> 引用，明文密钥请配置在服务器环境变量中。
              </li>
              <li>
                <Text strong>两种推送形态</Text>：填写应用凭证后可发
                <Tag color="blue">点对点工作通知</Tag>（精准 @ 人）；填写 Webhook
                可发<Tag color="geekblue">群机器人消息</Tag>。
              </li>
              <li>
                <Text strong>通知渠道</Text>：保存启用后，在「通知偏好 / 统一消息模板」
                里即可选择 {meta.label} 作为推送渠道。
              </li>
            </ul>
          }
        />

        <Card
          title={
            <Space>
              <ApiOutlined />
              {meta.label} 应用配置
              {configured ? (
                enabled ? (
                  <Tag icon={<CheckCircleOutlined />} color="success">
                    已启用
                  </Tag>
                ) : (
                  <Tag icon={<CloseCircleOutlined />} color="default">
                    已停用
                  </Tag>
                )
              ) : (
                <Tag color="warning">未配置</Tag>
              )}
            </Space>
          }
          extra={
            configured && (
              <Popconfirm title="确认删除该平台配置？" onConfirm={handleDelete}>
                <Button danger icon={<DisconnectOutlined />}>
                  删除配置
                </Button>
              </Popconfirm>
            )
          }
        >
          <Form form={form} layout="vertical" initialValues={{ status: true }}>
            <Form.Item label="集成名称" name="name" rules={[{ required: true }]}>
              <Input placeholder={`如：${meta.label} 企业应用`} />
            </Form.Item>

            <Form.Item label={meta.appIdLabel} name="app_id">
              <Input placeholder={meta.appIdPlaceholder} />
            </Form.Item>

            <Form.Item
              label="App Secret 环境变量名"
              name="app_secret_ref"
              extra={
                <Text type="secondary">{meta.secretEnvHint}（已配置时留空表示不修改）</Text>
              }
            >
              <Input.Password placeholder="如 DINGTALK_APP_SECRET（留空不修改）" autoComplete="new-password" />
            </Form.Item>

            {meta.needsAgentId && (
              <Form.Item label="AgentID / 应用ID" name="agent_id">
                <Input placeholder="应用详情页的 AgentID" />
              </Form.Item>
            )}

            <Form.Item
              label="群机器人 Webhook"
              name="webhook_url"
              extra={<Text type="secondary">{meta.webhookHelp}</Text>}
            >
              <Input placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
            </Form.Item>

            <Form.Item
              label="群机器人加签密钥（环境变量名）"
              name="webhook_secret_ref"
              extra={<Text type="secondary">开启加签时填写，如 DINGTALK_ROBOT_SECRET</Text>}
            >
              <Input.Password placeholder="如 DINGTALK_ROBOT_SECRET（留空不修改）" autoComplete="new-password" />
            </Form.Item>

            <Form.Item label="启用状态" name="status" valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="停用" />
            </Form.Item>

            <Form.Item>
              <Space>
                <Button type="primary" onClick={handleSave} loading={loading}>
                  保存配置
                </Button>
                <Button icon={<ThunderboltOutlined />} onClick={handleTest} loading={testing}>
                  测试连接
                </Button>
                {configured && (
                  <Popconfirm
                    title={`确认从${meta.label}同步组织架构？`}
                    description="将拉取部门与成员数据，已存在的账号会更新绑定关系"
                    onConfirm={handleSync}
                  >
                    <Button icon={<TeamOutlined />}>同步组织架构</Button>
                  </Popconfirm>
                )}
              </Space>
            </Form.Item>
          </Form>
        </Card>

        {configured && (
          <Card title={`已绑定的${meta.label}账号`} size="small">
            <Table<IntegrationBinding>
              dataSource={bindings}
              rowKey="id"
              size="small"
              pagination={{ pageSize: 10 }}
              locale={{ emptyText: '暂无绑定账号（用户扫码登录后自动生成）' }}
              columns={[
                { title: '用户ID', dataIndex: 'user_id', width: 280 },
                { title: '用户类型', dataIndex: 'user_type', width: 100 },
                { title: `${meta.label}账号`, dataIndex: 'external_id' },
                { title: '昵称', dataIndex: 'name' },
                {
                  title: '操作',
                  width: 100,
                  render: (_, record) => (
                    <Popconfirm title="确认解绑该账号？" onConfirm={() => handleUnbind(record.id)}>
                      <Button type="link" danger size="small">
                        解绑
                      </Button>
                    </Popconfirm>
                  ),
                },
              ]}
            />
          </Card>
        )}
      </Space>
    </Spin>
  );
}

export default function IntegrationsPage() {
  const access = useAccess();
  const [providers, setProviders] = useState<IntegrationProviderInfo[]>([]);
  const [activeKey, setActiveKey] = useState<IntegrationProvider>('dingtalk');

  const loadProviders = useCallback(async () => {
    try {
      const list = await integrationApi.listProviders();
      setProviders(list);
    } catch {
      setProviders([]);
    }
  }, []);

  useEffect(() => {
    loadProviders();
  }, [loadProviders]);

  const providerTabs: IntegrationProvider[] = ['dingtalk', 'wecom', 'feishu'];

  return (
    <PageContainer
      header={{
        title: '第三方集成',
        breadcrumb: {},
        extra: [
          <Descriptions key="status" size="small" column={1}>
            <Descriptions.Item>
              {providers.map((p) => (
                <Tag
                  key={p.provider}
                  color={p.configured ? (p.status === 1 ? 'success' : 'default') : 'warning'}
                  style={{ marginRight: 8 }}
                >
                  {p.name}：{p.configured ? (p.status === 1 ? '已启用' : '已停用') : '未配置'}
                </Tag>
              ))}
            </Descriptions.Item>
          </Descriptions>,
        ],
      }}
    >
      {!access.canIntegrationSettings ? (
        <Alert type="warning" message="您没有第三方集成配置权限" showIcon />
      ) : (
        <Card>
          <Tabs
            activeKey={activeKey}
            onChange={(k) => setActiveKey(k as IntegrationProvider)}
            items={providerTabs.map((p) => {
              const info = providers.find((x) => x.provider === p);
              return {
                key: p,
                label: (
                  <span>
                    {PROVIDER_FORM_META[p].label}
                    {info?.configured && (
                      <Tag
                        color={info.status === 1 ? 'success' : 'default'}
                        style={{ marginLeft: 8, marginRight: 0 }}
                      >
                        {info.status === 1 ? '启用' : '停用'}
                      </Tag>
                    )}
                  </span>
                ),
                children: (
                  <ProviderConfigTab
                    key={p}
                    provider={p}
                    providerInfo={info}
                    onSaved={loadProviders}
                  />
                ),
              };
            })}
          />
        </Card>
      )}
    </PageContainer>
  );
}
