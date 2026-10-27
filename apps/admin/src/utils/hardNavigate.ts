/**
 * 整页跳转（web / Tauri 桌面壳通用）。
 *
 * web（browser history）：保持 location.href = to 原语义。
 * Tauri 桌面壳生产态运行在自定义协议（tauri://localhost / http://tauri.localhost）上
 * 且为 hash 路由，直接写 '/login' 这类 pathname 会命中资产协议回退 → 整页重启后
 * hash 为空、umi 解析为 '/' → redirect /dashboard，丢失目的地。写成 '/#' + to：
 * 既保留「整页刷新、getInitialState 重跑、状态全重置」的原语义，hash 路由又能
 * 直接落到目标页（含查询串）。
 *
 * 全部 admin 内的 window.location.href 整页跳转都应走本函数，勿再直接赋值。
 */
import { isTauriDesktop } from '@hospital/api';

export const hardNavigate = (to: string): void => {
  window.location.href = isTauriDesktop() ? `/#${to}` : to;
};

/**
 * 当前路由路径（hash 路由感知）。
 *
 * 桌面壳（hash 路由）下 window.location.pathname 恒为 '/'，真实路由在
 * location.hash（形如 '#/dashboard?x=1'）；web（browser history）无路由 hash，
 * 仍走 pathname。用于性能/会话等「记录页面路径」的场景。
 */
export const currentRoutePath = (): string => {
  const { hash, pathname } = window.location;
  if (hash.startsWith('#/')) return hash.slice(1).split('?')[0] || '/';
  return pathname || '/';
};
