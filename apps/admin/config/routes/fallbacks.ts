/**
 * 兜底路由
 *
 * 必须位于路由数组末尾：
 *   - `/` 重定向到默认首页
 *   - `*` 渲染 404 页面（layout: false）
 *
 * 顺序敏感：放在任何业务路由之后、且 `'*'` 必须在最末，否则旧路径重定向会被通配吞掉。
 */
const fallbacks = [
  { path: '/', redirect: '/dashboard' },
  { path: '*', layout: false, component: './404' },
];

export default fallbacks;
