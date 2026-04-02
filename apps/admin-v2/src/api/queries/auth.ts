import { useMutation } from '@tanstack/react-query';
import { adminApi } from '@hospital/api';
import type { AdminLoginParams, AdminLoginResult } from '@hospital/api';
import { useAuthStore } from '@/auth/auth-store';
import { useNavigate } from 'react-router-dom';
import { STORAGE_KEYS } from '@hospital/shared';
import { getStorage } from '@hospital/shared';
import { HOME_PATH } from '@/config/app';
import { toast } from 'sonner';

export function useLoginMutation() {
  const login = useAuthStore(s => s.login);
  const navigate = useNavigate();

  return useMutation({
    mutationFn: (params: AdminLoginParams): Promise<AdminLoginResult> => {
      return adminApi.login(params);
    },
    onSuccess: (result) => {
      login(
        result.accessToken,
        result.refreshToken,
        result.admin,
        result.stores,
      );

      const lastPath = getStorage<string>(STORAGE_KEYS.LAST_PATH);
      navigate(lastPath || HOME_PATH, { replace: true });
    },
    onError: (error: any) => {
      toast.error(error.message || '登录失败，请检查用户名和密码');
    },
  });
}
