import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuthStore } from '@/auth/auth-store';
import { removeToken } from '@hospital/shared';
import { useNavigate } from 'react-router-dom';
import type { TenantStatusInfo } from '@hospital/shared';

export default function TenantSuspendedPage() {
  const tenantStatus = useAuthStore(s => s.tenantStatus) as TenantStatusInfo | null;
  const navigate = useNavigate();

  const title = tenantStatus?.status === 0
    ? '租户已被禁用'
    : tenantStatus?.status === 2
    ? '租户已欠费'
    : '订阅已到期';

  const description = tenantStatus?.status === 0
    ? '您的租户已被平台管理员禁用，请联系平台方处理。'
    : '您的订阅已到期或欠费，部分功能已暂停。请及时续费以恢复服务。';

  const handleLogout = () => {
    removeToken();
    localStorage.removeItem('hospital_tenant_suspended');
    navigate('/login', { replace: true });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center text-destructive">{title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-center text-sm text-muted-foreground">
          <p>{description}</p>
          {tenantStatus?.subscriptionEndAt && (
            <p>到期时间：{new Date(tenantStatus.subscriptionEndAt).toLocaleDateString('zh-CN')}</p>
          )}
          {tenantStatus?.contactPhone && (
            <p>续费请联系：<strong className="text-foreground">{tenantStatus.contactPhone}</strong></p>
          )}
        </CardContent>
        <CardFooter className="flex justify-center gap-3">
          <Button variant="outline" onClick={() => navigate('/dashboard')}>
            返回首页
          </Button>
          <Button onClick={handleLogout}>退出登录</Button>
        </CardFooter>
      </Card>
    </div>
  );
}
