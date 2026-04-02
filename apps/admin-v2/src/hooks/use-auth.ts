import { useAuthStore } from '@/auth/auth-store';

export function useAuth() {
  const { admin, currentStore, userStores, isLoading, login, logout, fetchCurrentUser, setCurrentStore, reset } = useAuthStore();
  return { admin, currentStore, userStores, isLoading, login, logout, fetchCurrentUser, setCurrentStore, reset };
}
