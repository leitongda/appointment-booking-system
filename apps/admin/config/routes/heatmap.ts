/**
 * 行为热力图
 *
 * URL：`/heatmap`
 *
 * 与「会话回放」同属运营分析域，复用 canAnalytics 权限
 * （仅超管或具备 statistics/system:log 权限可见）。
 *
 * 对应后端：GET /api/v1/session-events/heatmap
 */
const heatmap = [
  {
    path: '/heatmap',
    name: '热力图',
    icon: 'fire',
    access: 'canAnalytics',
    component: './heatmap',
  },
];

export default heatmap;
