/** 低代码搭建路由 */

export default [
  {
    path: '/platform/lowcode',
    name: '页面搭建',
    icon: 'EditOutlined',
    access: 'canLowcode',
    routes: [
      {
        path: '/platform/lowcode/list',
        name: '页面管理',
        component: './lowcode/list',
      },
      {
        path: '/platform/lowcode/marketplace',
        name: '模板市场',
        component: './lowcode/marketplace',
        access: 'canLowcodeMarketplace',
      },
      {
        path: '/platform/lowcode/marketplace/:id',
        name: '模板详情',
        component: './lowcode/marketplace/detail',
        hideInMenu: true,
        access: 'canLowcodeMarketplace',
      },
      {
        path: '/platform/lowcode/editor/:id',
        name: '编辑器',
        component: './lowcode/editor',
        hideInMenu: true,
      },
      {
        path: '/platform/lowcode/preview/:id',
        name: '预览',
        component: './lowcode/preview',
        hideInMenu: true,
      },
    ],
  },
];
