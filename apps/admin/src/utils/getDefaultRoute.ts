/**
 * 根据当前用户权限计算登录后 / 无权限时的默认落地路由，以及校验登录后回跳目标。
 *
 * ## 关键约束 —— 避开跳板路由 / 死循环
 * 路由树里大量父路径只是 `redirect` 跳板（如 `/medical-services` → `/medical-services/doctor`），
 * 且父节点的 access 多为聚合权限（`canClinicalOperations = canDoctor || canSchedule || ...`），
 * 用户可能满足聚合权限但所有子路由都无权限。若选中跳板，会触发再次 redirect → 死循环。
 *
 * 因此这里只收录「真正带 component 的叶子路由」+「该叶子自己的 access key」，
 * 不依赖父级聚合权限，也不选 redirect 跳板。
 *
 * ## 实现方式 —— 从路由树自动派生（单一事实来源）
 * 早期版本用一份**手工维护的白名单** `LEAF_ROUTE_CANDIDATES` 判定「哪些路径可回跳」，
 * 但项目有 80+ 条叶子路由分散在十余个配置文件，白名单严重滞后，导致用户从「未收录页面」
 * 退出登录后无法回到原路由（`isSafeReturnPath` 误判 → 走默认页）。
 *
 * 现改为运行时从真实路由树（`@config/routes`）派生全集（见 `deriveSafeRoutes.ts`），
 * 彻底消除漏配。落地路由仍保留**业务优先级顺序**（下方 `LANDING_PRIORITY`），
 * 用于从派生全集中挑出「最合适的默认落地页」。
 */

import { getSafeRouteMap } from './deriveSafeRoutes';

/** access 对象类型 —— 兼容 `src/access.ts` 返回值，读取时按 truthy 判定 */
type AccessMap = Record<string, unknown>;

/** 没有任何匹配时的最终兜底（避免返回空字符串导致跳转到当前页） */
const FALLBACK_PATH = '/dashboard';

/**
 * 登录后默认落地页的**业务优先级顺序**（仅用于排序，不是完整清单）。
 *
 * 维护约定：
 *   - 这里只列「期望的默认落地顺序」，越靠前优先级越高。
 *   - 实际是否可选仍由派生 Map（路由树真实存在）+ 用户权限共同决定，
 *     因此**即便此数组偶有滞后也不再致命** —— 最坏只是默认落地页次优，
 *     绝不会死循环或 403（派生 Map 保证选中的页面真实存在且用户有权限）。
 *   - 新增业务模块时，按期望的落地优先级在此追加即可。
 */
const LANDING_PRIORITY: ReadonlyArray<string> = [
  // 仪表盘（最高优先级）
  '/dashboard',

  // 医疗服务 - 核心业务
  '/medical-services/appointment/list',
  '/medical-services/schedule/rule',
  '/medical-services/schedule/list',
  '/medical-services/doctor/list',
  '/medical-services/patient/list',
  '/medical-services/medical-record',
  '/medical-services/follow-up/tasks',

  // 审批中心
  '/approval/instances',

  // 组织架构
  '/organization/store/list',
  '/organization/department/list',
  '/organization/staff',
  '/organization/medical-config/booking-rules',

  // 运营中心
  '/content-center/content/news',
  '/content-center/message/list',
  '/content-center/feedback',
  '/content-center/statistics',
  '/content-center/freelance/freelancers',

  // 系统管理
  '/system/role',
  '/system/config/hospital-info',
  '/system/blacklist',
  '/system/monitoring/log',
  '/system/data/import-export',

  // 平台管理（超管域）
  '/platform/operations-dashboard',
  '/platform/tenant/list',
  '/platform/tenant/plans',
  '/platform/miniapp-platform/company',
  '/platform/lowcode/list',
];

/**
 * 计算默认落地路由
 *
 * 优先从 `LANDING_PRIORITY` 中挑出第一个「在派生 Map 中存在且用户有权限」的路径；
 * 优先数组都不命中时，再按派生 Map 的自然顺序兜底（保证总能给出一个有权限的真实叶子路由）。
 *
 * @param access Umi access 对象（由 `src/access.ts` 返回，组件内通过 `useAccess()` 获取）
 * @returns 用户有权限的第一个叶子路由 path；都没有时返回 `/dashboard`
 */
export function getDefaultRoute(access: AccessMap | undefined | null): string {
  const safeMap = getSafeRouteMap();

  if (access) {
    // 1) 按业务优先级挑选
    for (const path of LANDING_PRIORITY) {
      const accessKey = safeMap.get(path);
      if (accessKey && access[accessKey]) {
        return path;
      }
    }
    // 2) 优先数组均不命中 —— 按派生 Map 自然顺序兜底
    for (const [path, accessKey] of safeMap) {
      if (access[accessKey]) {
        return path;
      }
    }
  }
  return FALLBACK_PATH;
}

/**
 * 校验「上次访问路径」是否可作为登录后的安全回跳目标
 *
 * 判定规则（数据来源为路由树派生 Map，自动覆盖全部真实叶子路由）：
 *   - 路径的 **pathname 部分**必须在派生 Map 中（即真实的、带 component 的稳定叶子路由，
 *     排除 redirect 跳板、详情页 `:id`、表单页 `/create` `/edit` 等）。
 *     比较时忽略 `search`/`hash`，因为 onPageChange 存入 LAST_PATH 的是完整路径
 *     （含分页/筛选 query），带参数的列表页同样应允许回跳以恢复用户原本视图状态。
 *   - 且用户对该路径有明确权限
 *
 * @param access Umi access 对象
 * @param fullPath 待校验的上次访问路径（可能含 `?query` / `#hash`）
 * @returns true 表示可安全回跳该路径（完整 fullPath 均可回跳）
 */
export function isSafeReturnPath(access: AccessMap | undefined | null, fullPath: string): boolean {
  if (!access || !fullPath) return false;

  // 仅取 pathname 部分，剥离可能的 ?query 与 #hash
  const pathname = fullPath.split(/[?#]/)[0];

  const accessKey = getSafeRouteMap().get(pathname);
  if (!accessKey) return false; // 不在真实叶子路由内（跳板、详情页、个人设置等）
  return !!access[accessKey];
}
