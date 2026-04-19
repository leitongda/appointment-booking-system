import Taro from '@tarojs/taro';
import { isTenantSuspended, type TenantStatusInfo } from '@hospital/shared';

const TENANT_STATUS_KEY = 'hospital_tenant_status';

let cachedTenantStatus: TenantStatusInfo | null = null;

export function setTenantStatus(status: TenantStatusInfo | null) {
  cachedTenantStatus = status;
  if (status) {
    try {
      Taro.setStorageSync(TENANT_STATUS_KEY, JSON.stringify(status));
    } catch { /* ignore */ }
  }
}

export function getTenantStatus(): TenantStatusInfo | null {
  if (cachedTenantStatus) return cachedTenantStatus;
  try {
    const raw = Taro.getStorageSync(TENANT_STATUS_KEY);
    if (raw) {
      cachedTenantStatus = JSON.parse(raw);
      return cachedTenantStatus;
    }
  } catch { /* ignore */ }
  return null;
}

export class TenantSuspendedError extends Error {
  constructor() {
    super('Tenant suspended');
    this.name = 'TenantSuspendedError';
  }
}

export function useTenantGuard() {
  return {
    requireWritable: () => {
      const status = getTenantStatus();
      if (isTenantSuspended(status)) {
        Taro.showModal({
          title: '该机构暂停服务',
          content: '该机构订阅已到期，暂不支持新预约，请联系机构续费。',
          showCancel: false,
          confirmText: '我知道了',
        });
        throw new TenantSuspendedError();
      }
    },
  };
}
