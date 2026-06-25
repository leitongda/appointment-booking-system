# Implementation Tasks: add-cms-module

## 阶段 1：后端数据模型与迁移

- [x] 1.1 新建 `app/models/cms.py`（CmsSite / CmsCategory / CmsArticle），含租户隔离、软删除、树形栏目
- [x] 1.2 在 `app/models/__init__.py` 注册 CMS 模型
- [x] 1.3 生成并清理 Alembic 迁移 `8de6e51b859f_add_cms_sites_categories_articles.py`（仅含 CMS 三表）
- [x] 1.4 应用迁移验证建表成功

## 阶段 2：后端模块与路由

- [x] 2.1 新建 `app/modules/cms/schemas.py`（Pydantic v2 Create/Update/Response，camelCase 别名）
- [x] 2.2 新建 `app/modules/cms/service.py`（CmsSiteService / CmsCategoryService / CmsArticleService）
- [x] 2.3 新建 `router_sites.py` / `router_categories.py`（含 tree）/ `router_articles.py`（含回收站 / 版本 / 已发布）
- [x] 2.4 在 `app/api/v1/__init__.py` 注册 3 个路由前缀
- [x] 2.5 在 `app/main.py` 的 OpenAPI tags 中新增 CMS 分组描述
- [x] 2.6 在 `scripts/init_permissions.py` 新增 `cms` 权限种子并执行入库

## 阶段 3：后端测试

- [x] 3.1 新建 `tests/unit/test_cms_services.py`，覆盖 CRUD / 筛选 / 租户隔离 / 树形 / 软删除 / 版本快照 / 门店过滤

## 阶段 4：前端 API 客户端

- [x] 4.1 新建 `packages/api/src/modules/cms.ts`（siteApi / categoryApi / articleApi + 类型）
- [x] 4.2 在 `packages/api/src/index.ts` 导出 CMS API 与类型

## 阶段 5：前端路由与权限

- [x] 5.1 新建 `apps/admin/config/routes/cms.ts`，注册到 `routes/index.ts`
- [x] 5.2 在 `src/access.ts` 新增 canCms / canCmsSite / canCmsCategory / canCmsArticle 权限门

## 阶段 6：前端页面

- [x] 6.1 站点：`sites.tsx`（列表）+ `site-form.tsx`（新增/编辑）
- [x] 6.2 栏目：`categories.tsx`（树形列表）+ `category-form.tsx`（新增/编辑，含父级选择）
- [x] 6.3 文章：`articles.tsx`（列表，站点/栏目/状态筛选）+ `article-form.tsx`（富文本 + 封面 + SEO）+ `article-detail.tsx`（只读详情）
- [x] 6.4 TypeScript 类型检查通过（tsc --noEmit）

## 阶段 7：联调与收尾（后续）

- [ ] 7.1 端到端联调（创建站点 → 栏目 → 文章 → 发布）
- [ ] 7.2 为超管/角色分配 cms 权限并验证菜单可见性
