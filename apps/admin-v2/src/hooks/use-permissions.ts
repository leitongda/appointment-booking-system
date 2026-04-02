import { useMemo } from 'react';
import { useAuthStore } from '@/auth/auth-store';
import { createPermissions } from '@/auth/permissions';

export function usePermissions() {
  const admin = useAuthStore(s => s.admin);
  return useMemo(() => createPermissions(admin), [admin]);
}
