/**
 * 会话回放
 *
 * URL 前缀：`/session-replay`
 *
 * 子路由：
 *   - 列表页：/session-replay
 *   - 回放页：/session-replay/:sessionId（hideInMenu，由列表「回放」按钮进入）
 *
 * 顶层 access: canAnalytics（与数据统计同权限域，仅超管或具备 statistics/system:log 权限可见）
 */
const sessionReplay = [
  {
    path: '/session-replay',
    name: '会话回放',
    icon: 'playCircle',
    access: 'canAnalytics',
    routes: [
      { path: '/session-replay', redirect: '/session-replay/list' },
      { path: '/session-replay/list', name: '会话列表', component: './session-replay' },
      {
        path: '/session-replay/:sessionId',
        name: '会话回放',
        component: './session-replay/replay',
        hideInMenu: true,
      },
    ],
  },
];

export default sessionReplay;
