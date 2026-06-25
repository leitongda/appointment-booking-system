import { useState, useEffect, useCallback } from 'react';
import { Card, App, List, Tag, Button, Popconfirm, Space, Spin, Empty } from 'antd';
import {
  ApiOutlined,
  LinkOutlined,
  DisconnectOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { adminApi, integrationApi, type IntegrationBindingItem } from '@hospital/api';

const PROVIDER_META: Record<string, { label: string; color: string }> = {
  dingtalk: { label: '钉钉', color: '#1677ff' },
  wecom: { label: '企业微信', color: '#07c160' },
  feishu: { label: '飞书', color: '#3370ff' },
};

/**
 * 账号设置 - 第三方账号绑定管理。
 *
 * 展示当前管理员已绑定的钉钉/企业微信/飞书账号，支持解绑。
 * 绑定操作通过登录页扫码完成（首次登录自动绑定），此处仅做查看与解绑。
 */
const IntegrationBindingsSection: React.FC = () => {
  const { message } = App.useApp();
  const [bindings, setBindings] = useState<IntegrationBindingItem[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.listIntegrationBindings();
      setBindings(data || []);
    } catch {
      setBindings([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleUnbind = async (id: string, provider: string) => {
    try {
      // 调用集成配置模块的解绑接口（integration_bindings 表）
      await integrationApi.removeBinding(provider as 'dingtalk' | 'wecom' | 'feishu', id);
      message.success('已解绑');
      setBindings((prev) => prev.filter((b) => b.id !== id));
    } catch (e: any) {
      message.error(e?.message || '解绑失败');
    }
  };

  return (
    <Card
      title={
        <Space>
          <ApiOutlined />
          第三方账号绑定
        </Space>
      }
      extra={
        <Button icon={<ReloadOutlined />} onClick={load} type="text" size="small">
          刷新
        </Button>
      }
    >
      <Spin spinning={loading}>
        <List<IntegrationBindingItem>
          dataSource={bindings}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <span>
                    暂未绑定任何第三方账号。
                    <br />
                    可在登录页使用钉钉/企业微信/飞书扫码登录时自动绑定。
                  </span>
                }
              />
            ),
          }}
          renderItem={(item) => {
            const meta = PROVIDER_META[item.provider] || { label: item.provider, color: '#999' };
            return (
              <List.Item
                actions={[
                  <Popconfirm
                    key="unbind"
                    title={`确认解绑${meta.label}账号？`}
                    onConfirm={() => handleUnbind(item.id, item.provider)}
                  >
                    <Button type="link" danger icon={<DisconnectOutlined />} size="small">
                      解绑
                    </Button>
                  </Popconfirm>,
                ]}
              >
                <List.Item.Meta
                  avatar={<LinkOutlined style={{ color: meta.color, fontSize: 20 }} />}
                  title={
                    <Space>
                      <Tag color={meta.color}>{meta.label}</Tag>
                      <span>{item.name || '未获取昵称'}</span>
                    </Space>
                  }
                  description={<span style={{ fontFamily: 'monospace' }}>{item.external_id}</span>}
                />
              </List.Item>
            );
          }}
        />
      </Spin>
    </Card>
  );
};

export default IntegrationBindingsSection;
