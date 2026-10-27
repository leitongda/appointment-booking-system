import React from 'react';
import { Button, Result, Space, Typography } from 'antd';
import { history, useModel } from '@umijs/max';
import { removeToken, removeStorage, STORAGE_KEYS } from '@hospital/shared';
import type { TenantStatusInfo } from '@hospital/shared';
import { hardNavigate } from '@/utils/hardNavigate';

const { Text, Paragraph } = Typography;

const TenantSuspendedPage: React.FC = () => {
  const { initialState } = useModel('@@initialState');
  const tenant = initialState?.currentUser?.tenant as TenantStatusInfo | undefined;

  const title = tenant?.status === 0
    ? '租户已被禁用'
    : tenant?.status === 2
    ? '租户已欠费'
    : '订阅已到期';

  const description = tenant?.status === 0
    ? '您的租户已被平台管理员禁用，请联系平台方处理。'
    : '您的订阅已到期或欠费，部分功能已暂停。请及时续费以恢复服务。';

  const handleLogout = () => {
    removeToken();
    removeStorage(STORAGE_KEYS.TENANT_SUSPENDED);
    hardNavigate('/login');
  };

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      background: 'var(--color-bg-layout)',
    }}>
      <Result
        status="error"
        title={title}
        subTitle={description}
        extra={[
          <Space key="info" style={{ marginBottom: 24 }}>
            {tenant?.subscriptionEndAt && (
              <Text type="secondary">
                到期时间：{new Date(tenant.subscriptionEndAt).toLocaleDateString('zh-CN')}
              </Text>
            )}
            {tenant?.contactPhone && (
              <Paragraph>
                续费请联系：<Text strong>{tenant.contactPhone}</Text>
              </Paragraph>
            )}
          </Space>,
          <div key="actions">
            <Button type="primary" onClick={handleLogout}>
              退出登录
            </Button>
            <Button style={{ marginLeft: 8 }} onClick={() => history.push('/dashboard')}>
              返回首页
            </Button>
          </div>,
        ]}
      />
    </div>
  );
};

export default TenantSuspendedPage;
