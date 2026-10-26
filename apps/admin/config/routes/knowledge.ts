/**
 * 知识库（RAG）
 *
 * URL 前缀：`/knowledge`
 *
 * 子菜单：
 *   - 知识库列表（我的 / 共享给我 / 租户公共）
 *   - 智能检索（语义检索，结果带引用来源）
 *   - 知识库详情（目录树 + 文档表 + 上传，hideInMenu）
 *
 * 顶层 access: canKnowledge（knowledge:read 或任一 knowledge:* 权限码）
 * 后端 KB_ENABLED=false 时接口整体 404，页面提示"功能未启用"。
 */
const knowledge = [
  {
    path: '/knowledge',
    name: '知识库',
    icon: 'book',
    access: 'canKnowledge',
    routes: [
      { path: '/knowledge', redirect: '/knowledge/bases' },
      { path: '/knowledge/bases', name: '知识库列表', component: './knowledge' },
      { path: '/knowledge/bases/:id', name: '知识库详情', component: './knowledge/detail', hideInMenu: true },
      { path: '/knowledge/search', name: '智能检索', component: './knowledge/search' },
    ],
  },
];

export default knowledge;
