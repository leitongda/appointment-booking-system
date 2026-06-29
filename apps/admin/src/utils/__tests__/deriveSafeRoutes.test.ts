import { describe, it, expect, beforeEach } from 'vitest';
import {
  getSafeRouteEntries,
  getSafeRouteMap,
  __resetSafeRouteCacheForTests,
  type AccessMap,
} from '../deriveSafeRoutes';
import { getDefaultRoute, isSafeReturnPath } from '../getDefaultRoute';

/**
 * 回归测试：登录后回跳 / 默认落地路由
 *
 * 背景 bug：`isSafeReturnPath` 原先用手工白名单判定「可回跳路径」，但白名单只收录了
 * ~20 条，而项目有 80+ 条真实叶子路由。用户从「未收录页面」（如排班列表、审批中心、
 * 通讯录）退出登录后，重新登录无法回到原路由。
 *
 * 这些测试用**真实的路由树**（`@config/routes`，未 mock）验证派生逻辑，因此同时守护
 * 未来新增路由时的正确性 —— 若新路由漏配 access 等问题会在此暴露。
 */

beforeEach(() => {
  __resetSafeRouteCacheForTests();
});

describe('getSafeRouteEntries / getSafeRouteMap', () => {
  it('包含原先被白名单遗漏的代表路径（回归 bug 的核心断言）', () => {
    const paths = new Set(getSafeRouteMap().keys());

    // 这些都是旧白名单没有、但真实存在的叶子路由 —— 是导致「回不去原路由」的元凶
    expect(paths.has('/medical-services/schedule/list')).toBe(true);
    expect(paths.has('/medical-services/schedule/calendar')).toBe(true);
    expect(paths.has('/medical-services/schedule/gantt')).toBe(true);
    expect(paths.has('/medical-services/schedule/custom')).toBe(true);
    expect(paths.has('/medical-services/schedule/rest-day')).toBe(true);
    expect(paths.has('/medical-services/schedule/room')).toBe(true);
    expect(paths.has('/medical-services/appointment/queue')).toBe(true);
    expect(paths.has('/medical-services/appointment/waitlist')).toBe(true);
    expect(paths.has('/approval/instances')).toBe(true);
    expect(paths.has('/approval/definitions')).toBe(true);
    expect(paths.has('/contacts/list')).toBe(true);
    expect(paths.has('/contacts/channels')).toBe(true);
    expect(paths.has('/cms/articles')).toBe(true);
    expect(paths.has('/attendance/shifts')).toBe(true);
    expect(paths.has('/finance/payment')).toBe(true);
    expect(paths.has('/finance/refund')).toBe(true);
    expect(paths.has('/platform/announcement/list')).toBe(true);
  });

  it('包含白名单里已有的稳定叶子路由（不回归已工作部分）', () => {
    const paths = new Set(getSafeRouteMap().keys());
    expect(paths.has('/dashboard')).toBe(true);
    expect(paths.has('/medical-services/doctor/list')).toBe(true);
    expect(paths.has('/medical-services/appointment/list')).toBe(true);
    expect(paths.has('/organization/store/list')).toBe(true);
    expect(paths.has('/system/role')).toBe(true);
  });

  it('排除 redirect 跳板（无 component 的聚合节点）', () => {
    const paths = new Set(getSafeRouteMap().keys());
    expect(paths.has('/medical-services')).toBe(false); // redirect -> doctor
    expect(paths.has('/medical-services/doctor')).toBe(false); // redirect -> doctor/list
    expect(paths.has('/medical-services/schedule')).toBe(false); // redirect -> rule
    expect(paths.has('/approval')).toBe(false); // redirect -> instances
    expect(paths.has('/')).toBe(false); // redirect -> dashboard
  });

  it('排除详情页 / 表单页（:id / create / edit 等）', () => {
    const paths = new Set(getSafeRouteMap().keys());
    expect(paths.has('/medical-services/doctor/:id')).toBe(false);
    expect(paths.has('/medical-services/doctor/create')).toBe(false);
    expect(paths.has('/medical-services/doctor/:id/edit')).toBe(false);
    expect(paths.has('/medical-services/appointment/:id')).toBe(false);
    expect(paths.has('/system/role/create')).toBe(false);
    expect(paths.has('/system/role/:id/edit')).toBe(false);
    expect(paths.has('/approval/instances/:id')).toBe(false);
    expect(paths.has('*')).toBe(false); // 通配 404 兜底
  });

  it('排除 layout:false 的非框架页（登录 / 404 / 低代码编辑器等）', () => {
    const paths = new Set(getSafeRouteMap().keys());
    expect(paths.has('/login')).toBe(false);
    expect(paths.has('/tenant-suspended')).toBe(false);
    // 低代码编辑器/预览是 layout:false
    expect(paths.has('/platform/lowcode/editor/:id')).toBe(false);
    expect(paths.has('/platform/lowcode/preview/:id')).toBe(false);
  });

  it('排除没有 access 键的叶子（如个人设置 —— 不应作为回跳目标）', () => {
    // /account/settings 无自身 access，也无带 access 的祖先
    const map = getSafeRouteMap();
    expect(map.has('/account/settings')).toBe(false);
  });

  it('每个条目都带有解析后的 access key（自身或最近祖先）', () => {
    const map = getSafeRouteMap();
    // 自身带 access
    expect(map.get('/dashboard')).toBe('canDashboard');
    expect(map.get('/medical-services/doctor/list')).toBe('canDoctor');
    // access 继承自最近祖先（如 schedule/list 的父级 schedule 声明了 canSchedule）
    // —— 只断言存在非空 accessKey，避免与具体 access 设计耦合过死
    for (const [path, accessKey] of map.entries()) {
      expect(accessKey, `path ${path} should have a non-empty accessKey`).toBeTruthy();
    }
  });

  it('Map 与 Entries 内容一致', () => {
    const entries = getSafeRouteEntries();
    const map = getSafeRouteMap();
    expect(entries.length).toBeGreaterThanOrEqual(map.size);
    for (const { path } of entries) {
      expect(map.has(path)).toBe(true);
    }
  });

  it('派生结果被缓存（多次调用返回同一引用）', () => {
    const a = getSafeRouteEntries();
    const b = getSafeRouteEntries();
    expect(a).toBe(b);
    const m1 = getSafeRouteMap();
    const m2 = getSafeRouteMap();
    expect(m1).toBe(m2);
  });
});

describe('isSafeReturnPath', () => {
  const fullAccess: AccessMap = new Proxy(
    {},
    { get: () => true }, // 所有权限都为 true
  );

  it('对原先漏掉的代表路径返回 true（有权限时）—— 回归 bug 核心断言', () => {
    expect(isSafeReturnPath(fullAccess, '/medical-services/schedule/list')).toBe(true);
    expect(isSafeReturnPath(fullAccess, '/medical-services/schedule/calendar?page=2')).toBe(true);
    expect(isSafeReturnPath(fullAccess, '/approval/instances')).toBe(true);
    expect(isSafeReturnPath(fullAccess, '/contacts/list#anchor')).toBe(true);
    expect(isSafeReturnPath(fullAccess, '/cms/articles')).toBe(true);
    expect(isSafeReturnPath(fullAccess, '/finance/payment?from=2024')).toBe(true);
  });

  it('忽略 query / hash，按 pathname 判定', () => {
    expect(isSafeReturnPath(fullAccess, '/medical-services/appointment/list?page=1&size=20')).toBe(true);
    expect(isSafeReturnPath(fullAccess, '/dashboard#section')).toBe(true);
  });

  it('对跳板 / 详情 / 表单页返回 false', () => {
    expect(isSafeReturnPath(fullAccess, '/medical-services')).toBe(false);
    expect(isSafeReturnPath(fullAccess, '/medical-services/doctor/123')).toBe(false);
    expect(isSafeReturnPath(fullAccess, '/system/role/create')).toBe(false);
    expect(isSafeReturnPath(fullAccess, '/login')).toBe(false);
  });

  it('用户无该路径权限时返回 false（即便路径本身可回跳）', () => {
    // 仅 dashboard 权限
    const access: AccessMap = { canDashboard: true };
    expect(isSafeReturnPath(access, '/dashboard')).toBe(true);
    expect(isSafeReturnPath(access, '/medical-services/doctor/list')).toBe(false);
    expect(isSafeReturnPath(access, '/approval/instances')).toBe(false);
  });

  it('空入参返回 false', () => {
    expect(isSafeReturnPath(fullAccess, '')).toBe(false);
    expect(isSafeReturnPath(null, '/dashboard')).toBe(false);
    expect(isSafeReturnPath(undefined, '/dashboard')).toBe(false);
  });
});

describe('getDefaultRoute', () => {
  it('超管（全权限）按优先级返回 /dashboard', () => {
    const fullAccess: AccessMap = new Proxy({}, { get: () => true });
    expect(getDefaultRoute(fullAccess)).toBe('/dashboard');
  });

  it('按业务优先级返回第一个有权限的路径', () => {
    // 去掉 dashboard，期望落到优先级下一档（appointment/list）
    const access: AccessMap = {
      canAppointment: true,
      canSchedule: true,
    };
    expect(getDefaultRoute(access)).toBe('/medical-services/appointment/list');
  });

  it('只有非优先数组中的权限时，按派生 Map 自然顺序兜底', () => {
    // canCmsArticle 不在 LANDING_PRIORITY 里，但派生 Map 含 /cms/articles
    const access: AccessMap = { canCmsArticle: true };
    const route = getDefaultRoute(access);
    expect(route).not.toBe('/dashboard'); // 无 dashboard 权限，不应兜底到 dashboard
    expect(route).toBeTruthy();
  });

  it('无任何权限时返回 /dashboard 兜底', () => {
    expect(getDefaultRoute({})).toBe('/dashboard');
    expect(getDefaultRoute(null)).toBe('/dashboard');
    expect(getDefaultRoute(undefined)).toBe('/dashboard');
  });

  it('永不返回跳板 / 详情页', () => {
    const fullAccess: AccessMap = new Proxy({}, { get: () => true });
    const route = getDefaultRoute(fullAccess);
    expect(route).not.toContain(':');
    expect(route).not.toBe('/');
    expect(route).not.toBe('*');
  });
});
