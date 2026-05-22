/**
 * 环境变量集中读取
 *
 * 把分散在 config.ts / proxy.ts 中的 `process.env.*` 读取统一到这里，
 * 便于其他子模块（webpack/proxy/...）共享同一组默认值。
 */

export const REACT_APP_ENV = process.env.REACT_APP_ENV || 'dev';

/**
 * API 基础路径，支持运行时通过环境变量覆盖
 */
export const API_BASE_URL = process.env.API_BASE_URL || '/api/v1';

/**
 * 代理目标，默认本地后端
 */
export const PROXY_TARGET = process.env.PROXY_TARGET || 'http://localhost:9000';

/**
 * 是否生产环境（用于 chainWebpack 等编译期判定）
 */
export const IS_PROD = process.env.NODE_ENV === 'production';

/**
 * 高德地图 API Key（构建期注入 headScripts）
 */
export const AMAP_KEY = process.env.AMAP_KEY || '';

/**
 * 高德地图服务代理地址（运行时供前端调用后端代理）
 */
export const AMAP_SERVICE_HOST = process.env.AMAP_SERVICE_HOST || '/_AMapService';
