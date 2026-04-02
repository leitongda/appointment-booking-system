import { create } from 'zustand';
import { adminApi, type Admin, type StoreInfo } from '@hospital/api';
import {
  setToken,
  removeToken,
  setStorage,
  removeStorage,
  resetTokenExpiredState,
  STORAGE_KEYS,
} from '@hospital/shared';

interface AuthState {
  admin: Admin | null;
  currentStore: StoreInfo | null;
  userStores: StoreInfo[];
  isLoading: boolean;

  login: (accessToken: string, refreshToken: string, admin: Admin, stores?: StoreInfo[]) => void;
  logout: () => Promise<void>;
  fetchCurrentUser: () => Promise<Admin | null>;
  setCurrentStore: (store: StoreInfo) => void;
  reset: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  admin: null,
  currentStore: null,
  userStores: [],
  isLoading: false,

  login: (accessToken, refreshToken, admin, stores) => {
    setToken(accessToken);
    setStorage(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
    resetTokenExpiredState();

    if (admin.tenantId) {
      setStorage(STORAGE_KEYS.CURRENT_TENANT_ID, admin.tenantId);
    }

    const storeList = stores || admin.stores || [];
    let currentStore: StoreInfo | null = null;
    if (storeList.length === 1) {
      currentStore = storeList[0] ?? null;
    } else if (storeList.length > 1) {
      const match = admin.currentStoreId
        ? storeList.find(s => s.id === admin.currentStoreId)
        : storeList[0];
      currentStore = match ?? storeList[0] ?? null;
    }

    if (currentStore) {
      setStorage(STORAGE_KEYS.STORE_CONTEXT, JSON.stringify(currentStore));
    }

    set({
      admin,
      currentStore,
      userStores: storeList,
    });
  },

  logout: async () => {
    try {
      await adminApi.logout();
    } catch {
      // 即使退出接口失败也要清理本地状态
    }
    get().reset();
  },

  fetchCurrentUser: async () => {
    set({ isLoading: true });
    try {
      const admin = await adminApi.getCurrentAdmin();
      const storeStr = localStorage.getItem(STORAGE_KEYS.STORE_CONTEXT);
      const currentStore = storeStr ? JSON.parse(storeStr) : null;
      const userStores = admin.stores || [];

      set({
        admin,
        currentStore,
        userStores,
        isLoading: false,
      });
      return admin;
    } catch {
      set({ isLoading: false });
      return null;
    }
  },

  setCurrentStore: (store) => {
    setStorage(STORAGE_KEYS.STORE_CONTEXT, JSON.stringify(store));
    set({ currentStore: store });
  },

  reset: () => {
    removeToken();
    removeStorage(STORAGE_KEYS.STORE_CONTEXT);
    removeStorage(STORAGE_KEYS.CURRENT_TENANT_ID);
    removeStorage(STORAGE_KEYS.LAST_PATH);
    set({
      admin: null,
      currentStore: null,
      userStores: [],
    });
  },
}));
