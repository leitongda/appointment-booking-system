/**
 * 代理条目工厂
 *
 * 把 dev/test/pre 中重复的 `{ target, changeOrigin, secure?, pathRewrite? }` 写法收敛到一处，
 * 通过参数表达「是否 rewrite /api 路径」「是否显式声明 secure」等差异。
 */

export interface ProxyEntryOptions {
  /**
   * 是否对 `/api` 前缀做路径改写（保留为同名前缀，等价于原配置中的 `{ '^/api': '/api' }`）
   */
  rewriteApi?: boolean;
  /**
   * 是否显式声明 `secure`；若为 `false` 则添加 `secure: false`，未传则不写入该字段（与原配置中 test/pre 行为一致）
   */
  secure?: boolean;
}

export const createProxy = (target: string, options: ProxyEntryOptions = {}) => {
  const entry: Record<string, unknown> = {
    target,
    changeOrigin: true,
  };

  if (options.secure === false) {
    entry.secure = false;
  }

  if (options.rewriteApi) {
    entry.pathRewrite = { '^/api': '/api' };
  }

  return entry;
};
