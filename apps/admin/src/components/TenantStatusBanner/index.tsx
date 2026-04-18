import React from 'react';
import { Alert, Button, Space } from 'antd';
import { history, useModel } from '@umijs/max';
import { deriveTenantBannerLevel } from '@hospital/shared';
import type { TenantStatusInfo } from '@hospital/shared';

const TenantStatusBanner: React.FC = () => {
  const { initialState } = useModel('@@initialState');
  const tenant = initialState?.currentUser?.tenant as TenantStatusInfo | undefined;

  const level = deriveTenantBannerLevel(tenant || null);

  if (level === 'none') return null;

  const days = tenant?.daysUntilExpiry;
  const contactPhone = tenant?.contactPhone;

  if (level === 'warning') {
    return (
      <Alert
        banner
        type="warning"
        showIcon
        message={
          <Space>
            <span>订阅将于 <strong>{days}</strong> 天后到期</span>
            {contactPhone && <span>请联系 {contactPhone} 续费</span>}
          </Space>
        }
      />
    );
  }

  // critical
  return (
    <Alert
      banner
      type="error"
      showIcon
      message={
        <Space>
          <span>
            {tenant?.status === 0
              ? '租户已被禁用'
              : tenant?.status === 2
              ? '租户已欠费，服务已暂停'
              : '订阅已到期，服务已暂停'}
          </span>
          {contactPhone && <span>请联系 {contactPhone} 续费</span>}
          <Button type="link" size="small" onClick={() => history.push('/tenant-suspended')}>
            查看详情
          </Button>
        </Space>
      }
    />
  );
};

export default TenantStatusBanner;
