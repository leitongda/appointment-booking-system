/**
 * 门店上下文 Provider
 * 
 * 功能：
 * 1. 从 URL 参数中获取 store 编码
 * 2. 验证门店是否有效
 * 3. 存储门店信息到 Context 和 localStorage
 * 4. 无效门店时显示错误页面
 */
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useSearchParams, history } from 'umi';
import { storeApi } from '@hospital/api';
import { 
  type StoreContext, 
  type Store,
  STORE_CONTEXT_KEY, 
  createStoreContext 
} from '@hospital/shared';
import { Result, Button, SpinLoading } from 'antd-mobile';

interface StoreProviderContextValue {
  /** 门店上下文信息 */
  store: StoreContext | null;
  /** 是否正在加载 */
  loading: boolean;
  /** 错误信息 */
  error: string | null;
  /** 重新加载门店信息 */
  reload: () => Promise<void>;
}

const StoreProviderContext = createContext<StoreProviderContextValue | null>(null);

/**
 * 获取门店上下文 Hook
 */
export function useStore(): StoreProviderContextValue {
  const context = useContext(StoreProviderContext);
  if (!context) {
    throw new Error('useStore must be used within a StoreProvider');
  }
  return context;
}

/**
 * 获取当前门店ID（便捷方法）
 */
export function getStoreId(): string | null {
  try {
    const stored = localStorage.getItem(STORE_CONTEXT_KEY);
    if (stored) {
      const context = JSON.parse(stored) as StoreContext;
      return context.storeId;
    }
  } catch {
    // ignore
  }
  return null;
}

/**
 * 获取当前门店上下文（便捷方法）
 */
export function getStoreContext(): StoreContext | null {
  try {
    const stored = localStorage.getItem(STORE_CONTEXT_KEY);
    if (stored) {
      return JSON.parse(stored) as StoreContext;
    }
  } catch {
    // ignore
  }
  return null;
}

interface StoreProviderProps {
  children: ReactNode;
}

/**
 * 门店 Provider 组件
 */
export const StoreProvider: React.FC<StoreProviderProps> = ({ children }) => {
  const [searchParams] = useSearchParams();
  const [store, setStore] = useState<StoreContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStore = async () => {
    setLoading(true);
    setError(null);

    try {
      // 1. 从 URL 获取门店编码
      const storeCode = searchParams.get('store');
      
      // 2. 优先尝试从 localStorage 恢复（app.tsx 已在启动时初始化）
      const cached = getStoreContext();
      
      // 3. 如果有 URL 参数且与缓存不同，重新验证
      if (storeCode && (!cached || cached.storeCode !== storeCode)) {
        // 调用 API 验证门店
        const storeData: Store = await storeApi.getByCode(storeCode);
        
        // 创建门店上下文并存储
        const context = createStoreContext(storeData);
        setStore(context);
        
        // 存储到 localStorage
        localStorage.setItem(STORE_CONTEXT_KEY, JSON.stringify(context));
      } else if (cached) {
        // 使用缓存的门店信息
        setStore(cached);
      } else {
        // 没有门店参数也没有缓存，显示错误
        setError('请通过正确的门店链接访问');
      }
      
    } catch (err: any) {
      console.error('加载门店信息失败:', err);
      
      // 清除可能过期的缓存
      localStorage.removeItem(STORE_CONTEXT_KEY);
      
      if (err.message?.includes('404') || err.message?.includes('不存在')) {
        setError('门店不存在或已停业');
      } else {
        setError('加载门店信息失败，请稍后重试');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStore();
  }, [searchParams.get('store')]);

  const contextValue: StoreProviderContextValue = {
    store,
    loading,
    error,
    reload: loadStore,
  };

  // 加载中状态
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <SpinLoading color="primary" style={{ '--size': '48px' }} />
          <p className="mt-4 text-muted-foreground">正在加载门店信息...</p>
        </div>
      </div>
    );
  }

  // 错误状态
  if (error || !store) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Result
          status="error"
          title="无法访问"
          description={error || '门店信息加载失败'}
        />
      </div>
    );
  }

  // 正常渲染
  return (
    <StoreProviderContext.Provider value={contextValue}>
      {children}
    </StoreProviderContext.Provider>
  );
};

export default StoreProvider;

