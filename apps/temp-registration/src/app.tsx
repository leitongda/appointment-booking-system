/**
 * Umi 运行时配置
 * 
 * 临时挂号应用入口
 */
import React from 'react';
import { storeApi } from '@hospital/api';
import { 
  type Store,
  STORE_CONTEXT_KEY, 
  createStoreContext 
} from '@hospital/shared';

/**
 * 从 URL 获取门店编码并初始化门店上下文
 * 在应用启动时执行一次
 */
const initStoreContext = async () => {
  try {
    // 从 URL 获取门店编码
    const urlParams = new URLSearchParams(window.location.search);
    const storeCode = urlParams.get('store');
    
    if (storeCode) {
      console.log('[TempReg] 从 URL 获取门店编码:', storeCode);
      
      // 调用 API 验证门店
      const storeData: Store = await storeApi.getByCode(storeCode);
      
      // 创建门店上下文并存储到 localStorage
      const context = createStoreContext(storeData);
      localStorage.setItem(STORE_CONTEXT_KEY, JSON.stringify(context));
      
      console.log('[TempReg] 门店上下文已初始化:', context.storeName);
    } else {
      // 检查是否有缓存的门店信息
      const cached = localStorage.getItem(STORE_CONTEXT_KEY);
      if (cached) {
        console.log('[TempReg] 使用缓存的门店上下文');
      } else {
        console.warn('[TempReg] 未指定门店，请通过正确的门店链接访问');
      }
    }
  } catch (error) {
    console.error('[TempReg] 初始化门店上下文失败:', error);
    // 清除可能过期的缓存
    localStorage.removeItem(STORE_CONTEXT_KEY);
  }
};

// 在应用启动时初始化门店（非阻塞）
initStoreContext();

/**
 * 修改根组件
 */
export function rootContainer(container: React.ReactNode) {
  return container;
}


