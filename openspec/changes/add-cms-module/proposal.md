# Change: 新增 CMS 内容站点模块（站点 / 栏目 / 文章）

## Why
系统现有 `content` 模块（新闻 / 公告 / 轮播图）面向单站点、门店级的运营内容，缺少一个面向「多站点门户」的完整内容管理能力。机构需要：
- 维护**多个站点**（官网、活动专题站等），每个站点有独立的栏目与文章；
- 用**树形栏目**组织内容结构（如「关于我们 → 团队 / 历史」）；
- 发布**富文本文章**，支持草稿 / 发布 / 下线、置顶、浏览统计与版本历史。

现有 `content` 模块无法表达「站点 → 栏目 → 文章」三级结构，也不支持多站点。因此新增独立的 `cms` 模块，与 `content` 解耦、职责清晰。

## What Changes
- 新增后端 `app/modules/cms/` 模块，提供站点 / 栏目 / 文章的完整 CRUD，含软删除回收站、版本快照、已发布列表公开接口。
- 新增数据模型 `CmsSite` / `CmsCategory`（树形）/ `CmsArticle`，租户级隔离（`tenant_id` 必填），文章可选归属门店（`store_id`）。
- 新增 Alembic 迁移创建 3 张表。
- 新增权限种子 `cms` / `cms:site:*` / `cms:category:*` / `cms:article:*`。
- 新增前端 `apps/admin/src/pages/cms/` 页面（站点 / 栏目 / 文章的列表 + 表单 + 详情），复用现有 ProTable / FormPage / RichTextEditor 基础设施。
- 新增 `packages/api/src/modules/cms.ts` API 客户端与 `apps/admin` 路由 + 权限门。

## Design Principles
- **解耦优先**：CMS 作为独立模块，不混入现有 `content`，避免语义混淆。
- **复用现有约定**：租户隔离参照 `contacts`、内容软删除与版本快照参照 `content`、树形栏目参照 `ContactGroup`。
- **多站点 CMS**：一个租户可拥有多个站点；栏目按站点组织；文章归属站点并可按门店细分。
- **渐进公开**：提供已发布文章的公开接口，便于后续 `apps/website` 等前端站点动态消费（本期不改动官网）。

## Scope

### In Scope
- 后端：`app/models/cms.py`、`app/modules/cms/`（schemas / service / router_*）、模型注册、Alembic 迁移、路由注册、OpenAPI tags、权限种子。
- 前端：`apps/admin/src/pages/cms/` 共 7 个页面（sites、site-form、categories、category-form、articles、article-form、article-detail）、`config/routes/cms.ts`、`src/access.ts` 权限门。
- 共享：`packages/api/src/modules/cms.ts` 及其导出。
- 后端单元测试 `tests/unit/test_cms_services.py`。

### Out of Scope
- 不改动现有 `content` 模块与 news / notice / banner 页面。
- 不改动 `apps/website`（官网动态化留待后续）。
- 不引入新的菜单信息架构重构，CMS 作为独立新一级菜单。
- 第一阶段不做栏目拖拽排序的前端交互（后端已提供排序接口）。

## Impact
- Affected specs: `cms-content-management` (new)
- Affected code:
  - `apps/server/app/models/cms.py` (new)
  - `apps/server/app/models/__init__.py`（注册模型）
  - `apps/server/app/modules/cms/`（new：schemas / service / router_sites / router_categories / router_articles / __init__）
  - `apps/server/app/api/v1/__init__.py`（注册 3 个路由）
  - `apps/server/app/main.py`（OpenAPI tags）
  - `apps/server/migrations/versions/8de6e51b859f_add_cms_sites_categories_articles.py` (new)
  - `apps/server/scripts/init_permissions.py`（cms 权限种子）
  - `apps/server/tests/unit/test_cms_services.py` (new)
  - `packages/api/src/modules/cms.ts` (new) + `packages/api/src/index.ts`
  - `apps/admin/config/routes/cms.ts` (new) + `config/routes/index.ts`
  - `apps/admin/src/access.ts`（canCms / canCmsSite / canCmsCategory / canCmsArticle）
  - `apps/admin/src/pages/cms/*` (new)
- 数据库：新增 3 张表（`cms_sites` / `cms_categories` / `cms_articles`）。
- 权限：新增 `cms` 菜单权限及其 12 个子权限。
