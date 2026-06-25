/**
 * 认证页面路由
 *
 * - /login：登录页
 * - /login/integration-callback：第三方扫码登录 OAuth 回调落地页
 * - /tenant-suspended：租户停用提示
 *
 * 三者均使用 `layout: false`，不在主框架内渲染。
 */
const auth = [
  { path: '/login', layout: false, component: './login' },
  { path: '/login/integration-callback', layout: false, component: './login/integration-callback' },
  { path: '/tenant-suspended', layout: false, component: './tenant-suspended' },
];

export default auth;
