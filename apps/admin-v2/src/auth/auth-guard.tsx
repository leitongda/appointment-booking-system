import { type ReactNode, useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/auth/auth-store';
import { getToken, getTenantSuspendedReason } from '@hospital/shared';
import { LOGIN_PATH } from '@/config/app';
import { Loader2 } from 'lucide-react';

interface AuthGuardProps {
  children: ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const location = useLocation();
  const { admin, fetchCurrentUser, isLoading, suspendReason, markTenantSuspended } = useAuthStore();
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (token && !admin) {
      fetchCurrentUser().finally(() => setInitialized(true));
    } else {
      setInitialized(true);
    }
    // 启动时从 localStorage 恢复暂停状态
    const reason = getTenantSuspendedReason();
    if (reason) {
      markTenantSuspended(reason);
    }
  }, []);

  const token = getToken();

  if (!token) {
    return <Navigate to={LOGIN_PATH} state={{ from: location }} replace />;
  }

  if (!initialized || isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!admin) {
    return <Navigate to={LOGIN_PATH} state={{ from: location }} replace />;
  }

  // 租户暂停时，只允许访问 tenant-suspended 页面
  if (suspendReason && location.pathname !== '/tenant-suspended') {
    return <Navigate to="/tenant-suspended" replace />;
  }

  return <>{children}</>;
}
