import { type ReactNode, useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/auth/auth-store';
import { getToken } from '@hospital/shared';
import { LOGIN_PATH } from '@/config/app';
import { Loader2 } from 'lucide-react';

interface AuthGuardProps {
  children: ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const location = useLocation();
  const { admin, fetchCurrentUser, isLoading } = useAuthStore();
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (token && !admin) {
      fetchCurrentUser().finally(() => setInitialized(true));
    } else {
      setInitialized(true);
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

  return <>{children}</>;
}
