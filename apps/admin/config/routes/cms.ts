/**
 * 内容站点（CMS）
 *
 * URL 前缀：`/cms`
 *
 * 子菜单：
 *   - 站点管理（canCmsSite）
 *   - 栏目管理（canCmsCategory）
 *   - 文章管理（canCmsArticle）
 *
 * 顶层 access: canCms
 */
const cms = [
  {
    path: '/cms',
    name: '内容站点',
    icon: 'global',
    access: 'canCms',
    routes: [
      { path: '/cms', redirect: '/cms/articles' },

      // 站点管理
      {
        path: '/cms/sites',
        name: '站点管理',
        access: 'canCmsSite',
        routes: [
          { path: '/cms/sites', component: './cms/sites' },
          { path: '/cms/sites/create', name: '新增站点', component: './cms/site-form', hideInMenu: true },
          { path: '/cms/sites/:id/edit', name: '编辑站点', component: './cms/site-form', hideInMenu: true },
        ],
      },

      // 栏目管理
      {
        path: '/cms/categories',
        name: '栏目管理',
        access: 'canCmsCategory',
        routes: [
          { path: '/cms/categories', component: './cms/categories' },
          {
            path: '/cms/categories/create',
            name: '新增栏目',
            component: './cms/category-form',
            hideInMenu: true,
          },
          {
            path: '/cms/categories/:id/edit',
            name: '编辑栏目',
            component: './cms/category-form',
            hideInMenu: true,
          },
        ],
      },

      // 文章管理
      {
        path: '/cms/articles',
        name: '文章管理',
        access: 'canCmsArticle',
        routes: [
          { path: '/cms/articles', component: './cms/articles' },
          {
            path: '/cms/articles/create',
            name: '发布文章',
            component: './cms/article-form',
            hideInMenu: true,
          },
          {
            path: '/cms/articles/:id/edit',
            name: '编辑文章',
            component: './cms/article-form',
            hideInMenu: true,
          },
          {
            path: '/cms/articles/:id/detail',
            name: '文章详情',
            component: './cms/article-detail',
            hideInMenu: true,
          },
        ],
      },
    ],
  },
];

export default cms;
