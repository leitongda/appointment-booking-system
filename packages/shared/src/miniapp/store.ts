/**
 * 小程序门店上下文工具
 *
 * 说明：
 * 小程序采用"每个门店独立发布"的模式，门店信息在构建时通过环境变量注入。
 * 构建命令示例：
 * TARO_APP_STORE_ID=xxx TARO_APP_STORE_CODE=beijing TARO_APP_STORE_NAME=北京门店 pnpm build:weapp
 */

import { type StoreContext } from '../types/store';

/**
 * 门店配置（从构建时环境变量读取）
 */
const storeConfig = {
  storeId: process.env.TARO_APP_STORE_ID || '',
  storeCode: process.env.TARO_APP_STORE_CODE || '',
  storeName: process.env.TARO_APP_STORE_NAME || '',
};

/**
 * 检查门店是否已配置
 */
export function isStoreConfigured(): boolean {
  return !!storeConfig.storeId;
}

/**
 * 获取门店ID
 */
export function getStoreId(): string {
  return storeConfig.storeId;
}

/**
 * 获取门店编码
 */
export function getStoreCode(): string {
  return storeConfig.storeCode;
}

/**
 * 获取门店名称
 */
export function getStoreName(): string {
  return storeConfig.storeName;
}

/**
 * 获取门店上下文
 */
export function getStoreContext(): StoreContext | null {
  if (!isStoreConfigured()) {
    return null;
  }

  return {
    storeId: storeConfig.storeId,
    storeCode: storeConfig.storeCode,
    storeName: storeConfig.storeName,
  };
}

/**
 * 验证门店配置
 * 在应用启动时调用，如果门店未配置则给出警告
 */
export function validateStoreConfig(): void {
  if (!isStoreConfigured()) {
    console.warn('⚠️ 门店未配置！请在构建时设置环境变量：');
    console.warn('  TARO_APP_STORE_ID=xxx');
    console.warn('  TARO_APP_STORE_CODE=store_code');
    console.warn('  TARO_APP_STORE_NAME=门店名称');
    console.warn('  示例: TARO_APP_STORE_ID=123 pnpm build:weapp');
  } else {
    console.log(`✓ 门店配置: ${storeConfig.storeName} (${storeConfig.storeCode})`);
    if (!storeConfig.storeCode) {
      console.warn('⚠️ 当前未配置 TARO_APP_STORE_CODE，患者端将无法通过公开接口稳定拉取门店默认主题。');
    }
  }
}
