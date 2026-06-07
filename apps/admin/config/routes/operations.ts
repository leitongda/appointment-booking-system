/**
 * 运营中心
 *
 * URL 前缀：`/content-center`
 *
 * 子菜单：
 *   - 内容管理（canContent，含 news / notice / banner）
 *   - 消息管理（canMessage，含 list / create / templates / recipient-rules）
 *   - 用户反馈（canFeedback）
 *   - 数据统计（canAnalytics）
 *
 * 顶层 access: canContentOperations
 */
const operations = [
  {
    path: '/freelance-portal',
    component: './freelance/portal',
    layout: false,
    hideInMenu: true,
  },
  {
    path: '/content-center',
    name: '运营中心',
    icon: 'notification',
    access: 'canContentOperations',
    routes: [
      { path: '/content-center', redirect: '/content-center/content' },
      {
        path: '/content-center/content',
        name: '内容管理',
        icon: 'fileText',
        access: 'canContent',
        routes: [
          { path: '/content-center/content', redirect: '/content-center/content/news' },
          { path: '/content-center/content/news', name: '新闻管理', component: './content/news' },
          { path: '/content-center/content/news/create', name: '发布新闻', component: './content/news-form', hideInMenu: true },
          { path: '/content-center/content/news/:id/edit', name: '编辑新闻', component: './content/news-form', hideInMenu: true },
          { path: '/content-center/content/news/:id/detail', name: '新闻详情', component: './content/news-detail', hideInMenu: true },
          { path: '/content-center/content/notice', name: '公告管理', component: './content/notice' },
          { path: '/content-center/content/notice/create', name: '发布公告', component: './content/notice-form', hideInMenu: true },
          { path: '/content-center/content/notice/:id/edit', name: '编辑公告', component: './content/notice-form', hideInMenu: true },
          { path: '/content-center/content/notice/:id/detail', name: '公告详情', component: './content/notice-detail', hideInMenu: true },
          { path: '/content-center/content/banner', name: '轮播图', component: './content/banner' },
          { path: '/content-center/content/banner/create', name: '新增轮播图', component: './content/banner-form', hideInMenu: true },
          { path: '/content-center/content/banner/:id/edit', name: '编辑轮播图', component: './content/banner-form', hideInMenu: true },
        ],
      },
      {
        path: '/content-center/message',
        name: '消息管理',
        icon: 'bell',
        access: 'canMessage',
        routes: [
          { path: '/content-center/message', redirect: '/content-center/message/list' },
          { path: '/content-center/message/list', name: '消息列表', component: './message' },
          { path: '/content-center/message/create', name: '发送消息', component: './message/form', hideInMenu: true },
          { path: '/content-center/message/templates', name: '统一模板', component: './message/templates' },
          { path: '/content-center/message/recipient-rules', name: '收件人规则', component: './message/recipient-rules' },
        ],
      },
      {
        path: '/content-center/feedback',
        name: '用户反馈',
        icon: 'comment',
        component: './feedback',
        access: 'canFeedback',
      },
      {
        path: '/content-center/support',
        name: '工单支持',
        icon: 'customerService',
        component: './support',
        access: 'canSupportTicket',
      },
      {
        path: '/content-center/points',
        name: '积分管理',
        icon: 'gift',
        component: './points',
        access: 'canPoints',
      },
      {
        path: '/content-center/statistics',
        name: '数据统计',
        icon: 'lineChart',
        component: './system/analytics',
        access: 'canAnalytics',
      },
      {
        path: '/content-center/freelance',
        name: '兼职费用',
        icon: 'team',
        access: 'canFreelance',
        routes: [
          { path: '/content-center/freelance', redirect: '/content-center/freelance/freelancers' },
          { path: '/content-center/freelance/freelancers', name: '兼职人员', component: './freelance/freelancers' },
          { path: '/content-center/freelance/tasks', name: '任务管理', component: './freelance/tasks' },
          { path: '/content-center/freelance/settlements', name: '结算管理', component: './freelance/settlements' },
          { path: '/content-center/freelance/statistics', name: '费用统计', component: './freelance/statistics' },
          { path: '/content-center/freelance/data-collection', name: '数据采集', component: './freelance/data-collection' },
        ],
      },
    ],
  },
];

export default operations;
