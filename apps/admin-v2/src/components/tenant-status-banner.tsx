import { useAuthStore } from '@/auth/auth-store';
import { deriveTenantBannerLevel, type TenantStatusInfo } from '@hospital/shared';
import { useNavigate } from 'react-router-dom';

export function TenantStatusBanner() {
  const tenantStatus = useAuthStore(s => s.tenantStatus) as TenantStatusInfo | null;
  const navigate = useNavigate();

  const level = deriveTenantBannerLevel(tenantStatus);
  if (level === 'none') return null;

  const days = tenantStatus?.daysUntilExpiry;
  const contactPhone = tenantStatus?.contactPhone;

  if (level === 'warning') {
    return (
      <div className="border-b bg-yellow-50 dark:bg-yellow-950 px-4 py-2 text-sm text-yellow-800 dark:text-yellow-200 flex items-center gap-2">
        <span>订阅将于 <strong>{days}</strong> 天后到期</span>
        {contactPhone && <span>请联系 {contactPhone} 续费</span>}
      </div>
    );
  }

  // critical
  return (
    <div className="border-b bg-red-50 dark:bg-red-950 px-4 py-2 text-sm text-red-800 dark:text-red-200 flex items-center gap-2">
      <span>
        {tenantStatus?.status === 0
          ? '租户已被禁用'
          : tenantStatus?.status === 2
          ? '租户已欠费，服务已暂停'
          : '订阅已到期，服务已暂停'}
      </span>
      {contactPhone && <span>请联系 {contactPhone} 续费</span>}
      <button
        className="underline font-medium ml-2"
        onClick={() => navigate('/tenant-suspended')}
      >
        查看详情
      </button>
    </div>
  );
}
