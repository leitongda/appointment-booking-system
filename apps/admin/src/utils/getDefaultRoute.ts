/**
 * 根据当前用户权限计算登录后 / 无权限时的默认落地路由
 *
 * 背景：
 *   - 登录页原先硬编码跳转 `/dashboard`，若用户无 dashboard 权限会进入死循环
 *     （`/dashboard` 无权限 → `onUnAccessible` 又跳回 `/dashboard`）
 *   - 这里按业务优先级返回「用户有权限的第一个叶子路由」作为兜底落地页
 *
 * 关键约束 —— 避开跳板路由：
 *   路由树里大量父路径只是 `redirect` 跳板（如 `/medical-services` → `/medical-services/doctor`），
 *   且父节点的 access 多为聚合权限（`canClinicalOperations = canDoctor || canSchedule || ...`），
 *   用户可能满足聚合权限但所有子路由都无权限。若选中跳板，会触发再次 redirect → 死循环。
 *   因此这里只收录「真正带 component 的叶子路径」+「该叶子自己的 access key」，
 *   不依赖父级聚合权限，也不选 redirect 跳板。
 *
 * access key 必须与 `apps/admin/src/access.ts` 的返回字段一一对应；
 * 顺序代表业务优先级（仪表盘优先，其次核心业务，最后系统/平台管理）。
 */

/**
 * access 对象类型 —— 兼容 `src/access.ts` 的返回值
 *
 * access.ts 返回一个固定形状的对象：大部分字段是 `boolean | undefined`，
 * 但也包含 `hasPermission` 等函数字段。这里用宽松索引签名（unknown）兼容，
 * 内部读取时统一按 truthy 判定（`!!access[accessKey]`）。
 */
type AccessMap = Record<string, unknown>;

/**
 * 叶子路由白名单 —— [path, accessKey] 有序数组
 *
 * 维护约定：
 *   - 仅收录有 `component` 的叶子路由（不要把 redirect 跳板、layout 容器放进来）
 *   - accessKey 取该叶子路由在 routes 里声明的 `access` 字段（没有则取其最近父级的 access）
 *   - 新增业务路由时，在此表追加对应条目即可被自动纳入候选
 */
const LEAF_ROUTE_CANDIDATES: ReadonlyArray<readonly [string, string]> = [
  // 仪表盘（最高优先级）
  ['/dashboard', 'canDashboard'],

  // 医疗服务 - 核心业务
  ['/medical-services/appointment/list', 'canAppointment'],
  ['/medical-services/schedule/rule', 'canSchedule'],
  ['/medical-services/doctor/list', 'canDoctor'],
  ['/medical-services/patient/list', 'canPatient'],
  ['/medical-services/medical-record', 'canMedicalRecord'],
  ['/medical-services/follow-up/tasks', 'canMedicalRecord'],

  // 组织架构
  ['/organization/store/list', 'canStore'],
  ['/organization/department/list', 'canDepartment'],
  ['/organization/staff', 'canUserManagement'],
  ['/organization/medical-config/booking-rules', 'canMedicalConfig'],

  // 运营中心
  ['/content-center/content/news', 'canContent'],
  ['/content-center/message/list', 'canMessage'],
  ['/content-center/feedback', 'canFeedback'],
  ['/content-center/statistics', 'canAnalytics'],
  ['/content-center/freelance/freelancers', 'canFreelance'],

  // 系统管理
  ['/system/role', 'canRoleManagement'],
  ['/system/config/hospital-info', 'canSystemConfig'],
  ['/system/blacklist', 'canBlacklistSettings'],
  ['/system/monitoring/log', 'canSystemMonitoring'],
  ['/system/data/import-export', 'canSystemMonitoring'],

  // 平台管理（超管域）
  ['/platform/operations-dashboard', 'canPlatformMetrics'],
  ['/platform/tenant/list', 'canTenant'],
  ['/platform/tenant/plans', 'canTenantPlans'],
  ['/platform/miniapp-platform/company', 'canMiniappPlatform'],
  ['/platform/lowcode/list', 'canLowcode'],

  // 注：以下模块的 access key（canFinanceManagement / canApproval /
  // canPlatformAnnouncement / canSupportTicket / canPoints 等）在
  // access.ts 中尚未定义，对应路由当前对所有用户均不可达，
  // 故暂不纳入候选。待 access.ts 补全后再追加。
];

/** 没有任何匹配时的最终兜底（避免返回空字符串导致跳转到当前页） */
const FALLBACK_PATH = '/dashboard';

/**
 * 计算默认落地路由
 *
 * @param access Umi access 对象（由 `src/access.ts` 返回，组件内通过 `useAccess()` 获取）
 * @returns 第一个有权限的叶子路由 path；都没有时返回 `/dashboard`
 */
export function getDefaultRoute(access: AccessMap | undefined | null): string {
  if (access) {
    for (const [path, accessKey] of LEAF_ROUTE_CANDIDATES) {
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
 * 用于登录后回跳 lastPath 前的校验：若上次路径因无权限被踢出，
 * 或是个 redirect 跳板（回跳会触发再次 redirect → 可能死循环），
 * 则不应回跳，改用默认路由。
 *
 * 判定规则：
 *   - 路径必须在白名单内（即稳定的列表/首页入口，排除 redirect 跳板、详情页 `:id` 等）
 *   - 且用户对该路径有明确权限
 *
 * @param access Umi access 对象
 * @param pathname 待校验的上次访问路径
 * @returns true 表示可安全回跳该路径
 */
export function isSafeReturnPath(access: AccessMap | undefined | null, pathname: string): boolean {
  if (!access || !pathname) return false;
  for (const [path, accessKey] of LEAF_ROUTE_CANDIDATES) {
    if (path === pathname) {
      return !!access[accessKey];
    }
  }
  // 不在白名单内（跳板、详情页、个人设置等）一律不作为登录后首跳目标。
  return false;
}
