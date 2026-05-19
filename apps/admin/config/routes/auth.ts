/**
 * 认证页面路由
 *
 * - /login：登录页
 * - /tenant-suspended：租户停用提示
 *
 * 二者均使用 `layout: false`，不在主框架内渲染。
 */
const auth = [
  { path: '/login', layout: false, component: './login' },
  { path: '/tenant-suspended', layout: false, component: './tenant-suspended' },
];

export default auth;
