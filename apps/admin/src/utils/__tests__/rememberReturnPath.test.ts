import { describe, it, expect } from 'vitest';
import { isReturnablePathname } from '@hospital/shared';

/**
 * 回归测试：所有「跳登录」路径复用 rememberReturnPath 记忆 LAST_PATH，
 * 其排除规则由 isReturnablePathname 决定。这里守护该纯函数的边界。
 *
 * 背景：会话失效/被动登出（401 拦截器、Tab 切入 token 过期、跨 Tab 登出、
 * 刷新时 token 过期、无 token 导航）原先都不记忆路径，导致重新登录后回不到原页面。
 * 现统一通过 rememberReturnPath 记忆；本测试锁定其「哪些路径该记 / 不该记」的契约。
 */
describe('isReturnablePathname', () => {
  it('排除公共入口 / 错误 / 租户停用页（回跳到它们无意义）', () => {
    expect(isReturnablePathname('/login')).toBe(false);
    expect(isReturnablePathname('/')).toBe(false);
    expect(isReturnablePathname('/welcome')).toBe(false);
    expect(isReturnablePathname('/404')).toBe(false);
    expect(isReturnablePathname('/403')).toBe(false);
    expect(isReturnablePathname('/tenant-suspended')).toBe(false);
  });

  it('业务页面均视为可回跳', () => {
    expect(isReturnablePathname('/dashboard')).toBe(true);
    expect(isReturnablePathname('/medical-services/schedule/list')).toBe(true);
    expect(isReturnablePathname('/approval/instances')).toBe(true);
    expect(isReturnablePathname('/contacts/list')).toBe(true);
    expect(isReturnablePathname('/finance/payment')).toBe(true);
    expect(isReturnablePathname('/cms/articles')).toBe(true);
  });

  it('空入参返回 false（安全 no-op）', () => {
    expect(isReturnablePathname(undefined)).toBe(false);
    expect(isReturnablePathname(null as unknown as string)).toBe(false);
    expect(isReturnablePathname('')).toBe(false);
  });
});
