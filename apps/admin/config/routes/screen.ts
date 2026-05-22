/**
 * 可视化大屏路由
 */
const screen = [
  {
    path: '/screen',
    name: '数据大屏',
    icon: 'lineChart',
    component: './screen',
    layout: false, // 禁用默认的 ProLayout 模板以支持全屏显示
    access: 'canDashboard',
  },
];

export default screen;
