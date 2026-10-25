/**
 * 从路由配置树自动派生「可安全回跳的叶子路由 + 其 access key」。
 *
 * 背景：
 *   `getDefaultRoute` / `isSafeReturnPath` 原先依赖一份**手工维护**的白名单
 *   (`LEAF_ROUTE_CANDIDATES`)，但项目路由分散在 `config/routes/` 下十余个文件、
 *   80+ 条叶子路由，白名单严重滞后，导致用户从「未收录页面」退出登录后，
 *   重新登录无法回到原路由（`isSafeReturnPath` 返回 false → 走默认页）。
 *
 *   这里改为运行时直接导入路由树（`@config/routes`，普通 TS 模块，可在 src 使用），
 *   按「安全回跳」的既有约定自动派生全集，作为单一事实来源，彻底消除漏配。
 *
 * 派生规则（与旧白名单的安全意图一一对应）：
 *   - 跳过 `layout: false`（登录页 / 404 / 租户停用 / 低代码编辑器预览等非框架页）
 *   - 跳过带 `redirect` 的节点（无 component 的跳板）
 *   - 跳过无 `component` 的节点（纯容器 / 布局节点）
 *   - 跳过详情/表单类路径：含 `:param`、`*`，或以 `/create`、`/edit`、`/detail`、
 *     `/audit`、`/permissions`、`/form` 结尾
 *   - 跳过公共入口路径 `/login`、`/welcome`、`/404`、`/403`、`/tenant-suspended`
 *   - `accessKey` 取「该叶子自身 access，否则最近祖先 access」；
 *     没有任何祖先带 access 的叶子（如个人设置、操作指引）保守排除
 *     —— 保留「必须有明确权限才能作为回跳目标」的不变量，避免无限回跳。
 */

// 路由配置节点（松散类型，匹配 config/routes 下各文件里的对象字面量）
interface RouteNode {
  path?: string;
  redirect?: string;
  component?: string;
  access?: string;
  layout?: boolean;
  routes?: RouteNode[];
  hideInMenu?: boolean;
  [key: string]: unknown;
}

/** access 对象类型 —— 兼容 `src/access.ts` 返回值，读取时按 truthy 判定 */
type AccessMap = Record<string, unknown>;

/** 派生结果项 */
import ALL_ROUTES from '@config/routes';

export interface SafeRouteEntry {
  path: string;
  accessKey: string;
}

/** 公共入口/非业务路径 —— 不作为回跳目标 */
const NON_BUSINESS_PATHS = new Set(['/login', '/welcome', '/404', '/403', '/tenant-suspended']);

/** 详情/表单类路径后缀 —— 回跳不稳定（表单可能已失效、详情 id 可能已变） */
const UNSTABLE_SUFFIXES = ['/create', '/edit', '/detail', '/audit', '/permissions', '/form'];

/**
 * 判断路径是否「不稳定」（详情页 / 表单页 / 通配 / 带路径参数）
 *
 * 与旧 `isSafeReturnPath` 白名单的「仅稳定列表/首页入口」意图一致。
 */
function isUnstablePath(path: string): boolean {
  if (!path) return true;
  if (path.includes('*')) return true; // 通配兜底
  if (path.includes('/:')) return true; // 路径参数（:id 等）
  return UNSTABLE_SUFFIXES.some((suffix) => path.endsWith(suffix));
}

/**
 * 递归收集可安全回跳的叶子路由。
 *
 * @param nodes    当前层的路由节点
 * @param inheritedAccess  从祖先继承下来的 access key（叶子自身未声明时使用）
 * @param out      累积输出
 */
function collect(nodes: RouteNode[] | undefined, inheritedAccess: string | undefined, out: SafeRouteEntry[]): void {
  if (!Array.isArray(nodes)) return;

  for (const node of nodes) {
    // layout:false 的整棵子树都跳过（登录页、404、低代码编辑器等非框架页）
    if (node.layout === false) continue;

    const path = node.path;
    // 当前节点生效的 access key：自身优先，否则继承祖先
    const nodeAccess = node.access || inheritedAccess;

    // 叶子判定：有 component、非 redirect 跳板、非通配/详情/表单、非公共入口
    const isLeaf =
      !!path &&
      !!node.component &&
      !node.redirect &&
      !NON_BUSINESS_PATHS.has(path) &&
      !isUnstablePath(path);

    if (isLeaf && nodeAccess) {
      out.push({ path: path!, accessKey: nodeAccess });
    }

    // 继续向子节点递归（即使当前节点是叶子，也可能其 routes 里有更深叶子）
    if (node.routes && node.routes.length > 0) {
      collect(node.routes, nodeAccess, out);
    }
  }
}

/** 模块级缓存：派生计算只执行一次 */
let cachedEntries: SafeRouteEntry[] | null = null;

/**
 * 派生并缓存「可安全回跳叶子路由」全集。
 *
 * 结果按路由树的自然顺序（即 `config/routes/index.ts` 的聚合顺序 + 各文件内部顺序），
 * 该顺序同时也是 `getDefaultRoute` 在优先数组都不命中时的兜底顺序。
 */
export function getSafeRouteEntries(): SafeRouteEntry[] {
  if (cachedEntries) return cachedEntries;

  const out: SafeRouteEntry[] = [];
  collect(ALL_ROUTES, undefined, out);
  cachedEntries = out;
  return out;
}

/**
 * 以 path 为键的查找表（带 access key），用于 O(1) 判定「路径是否可回跳 + 需何权限」。
 *
 * 同一路径在路由树里若被声明多次（极少见），以**首次出现**为准 ——
 * 与 Umi「先匹配先生效」的路由解析顺序一致。
 */
let cachedMap: Map<string, string> | null = null;

export function getSafeRouteMap(): Map<string, string> {
  if (cachedMap) return cachedMap;
  const map = new Map<string, string>();
  for (const { path, accessKey } of getSafeRouteEntries()) {
    if (!map.has(path)) {
      map.set(path, accessKey);
    }
  }
  cachedMap = map;
  return map;
}

/**
 * 重置模块缓存。仅供单元测试使用：测试间需要切换 mock 的路由树时调用。
 * @internal
 */
export function __resetSafeRouteCacheForTests(): void {
  cachedEntries = null;
  cachedMap = null;
}

// 真实路由树：从配置聚合入口导入（运行时可用的普通 TS 模块）。
// 单元测试通过 `vi.mock('@config/routes', ...)` 替换该模块的默认导出来注入桩数据。

export type { AccessMap };
