/**
 * 整页跳转（web / Tauri 桌面壳通用）——与 apps/admin/src/utils/hardNavigate.ts 同构。
 *
 * web（browser history）：保持 location.href = to 原语义。
 * Tauri 桌面壳生产态运行在自定义协议（tauri://localhost / http://tauri.localhost）上
 * 且为 hash 路由，直接写 '/login' 这类 pathname 会命中资产协议回退 → 整页重启后
 * hash 为空、umi 解析为 '/' → redirect /dashboard，丢失目的地。写成 '/#' + to：
 * 既保留「整页刷新、状态全重置」的原语义，hash 路由又能直接落到目标页。
 */
import { isTauriDesktop } from '@hospital/api';

export const hardNavigate = (to: string): void => {
  window.location.href = isTauriDesktop() ? `/#${to}` : to;
};
