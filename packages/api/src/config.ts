/**
 * API 配置
 * 提供默认配置值，各端可在初始化时覆盖
 */

/** API 配置接口 */
export interface ApiConfig {
  /** API 基础路径前缀 */
  prefix: string;
  /** API 版本号 */
  version: string;
}

/** 默认 API 配置 */
export const API_CONFIG: ApiConfig = {
  prefix: '/api',
  version: 'v1',
};

/**
 * 获取完整的 API 基础 URL
 * @returns 拼接后的基础 URL，如 '/api/v1'
 */
export const getApiBaseUrl = (): string => {
  return `${API_CONFIG.prefix}/${API_CONFIG.version}`;
};

/**
 * 设置 API 配置
 * @param config 部分配置，会与现有配置合并
 */
export const setApiConfig = (config: Partial<ApiConfig>): void => {
  Object.assign(API_CONFIG, config);
};

/**
 * 重置 API 配置为默认值
 */
export const resetApiConfig = (): void => {
  API_CONFIG.prefix = '/api';
  API_CONFIG.version = 'v1';
};

