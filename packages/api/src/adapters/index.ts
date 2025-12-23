/**
 * 请求适配器导出
 * 用于非浏览器环境（如小程序）的 HTTP 请求封装
 */

export { createTaroAdapter, getTaroToken, setTaroToken } from './taro';
export type { TaroAdapterConfig } from './taro';

