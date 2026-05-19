/**
 * 个人设置
 *
 * `hideInMenu: true`，仅通过用户头像下拉等入口进入。
 */
const account = [
  {
    path: '/account',
    hideInMenu: true,
    routes: [
      { path: '/account', redirect: '/account/settings' },
      { path: '/account/settings', name: '个人设置', component: './account/settings' },
    ],
  },
];

export default account;
