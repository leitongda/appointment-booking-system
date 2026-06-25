# Spec Delta: cms-content-management

## ADDED Requirements

### Requirement: CMS 数据必须按租户隔离

CMS 站点、栏目、文章均带 `tenant_id` 且必填。所有列表与详情查询必须只返回当前管理员所属租户的数据，跨租户访问必须被拒绝。

#### Scenario: 管理员查询站点列表

- WHEN 一个属于租户 A 的管理员请求 `GET /api/v1/cms/sites`
- THEN 返回的列表只包含租户 A 的站点
- AND 租户 B 的站点不会出现在结果中

#### Scenario: 管理员访问其他租户的文章详情

- WHEN 一个属于租户 A 的管理员请求 `GET /api/v1/cms/articles/{id}`，而该文章属于租户 B
- THEN 返回 404

### Requirement: 站点必须在租户内拥有唯一编码

每个站点有一个 `code`，同一租户下站点编码唯一，用于业务标识与站点定位。

#### Scenario: 创建编码重复的站点

- WHEN 在租户 A 下创建第二个 `code="main"` 的站点
- THEN 创建失败并提示编码已存在

### Requirement: 栏目按站点组织且支持树形层级

栏目归属站点，同一站点内栏目标识（slug）唯一，并支持多级父子层级。

#### Scenario: 获取栏目树

- WHEN 管理员请求 `GET /api/v1/cms/categories/tree?siteId={siteId}`
- THEN 返回该站点下栏目的嵌套树结构，子栏目挂在父栏目的 children 下

#### Scenario: 创建栏目时指定父级

- WHEN 创建一个栏目并指定 `parentId` 为同站点下已存在的栏目
- THEN 该栏目成为指定父级栏目的子栏目

### Requirement: 文章必须支持草稿、发布、下线三种状态

文章 `status` 为 0（草稿）/ 1（已发布）/ 2（已下线）。首次发布时系统自动记录发布时间。

#### Scenario: 创建并直接发布文章

- WHEN 创建文章时 `status=1`
- THEN 文章状态为已发布，且 `publishTime` 被自动设置为当前时间

#### Scenario: 草稿文章不出现在已发布列表

- WHEN 请求 `GET /api/v1/cms/articles/published?siteId={siteId}`
- THEN 返回结果只包含 status=1 的文章，草稿文章被排除

### Requirement: 文章可选归属门店，门店过滤命中门店级与站点级内容

文章的 `storeId` 可空（站点级）。按门店过滤时，命中该门店的文章以及所有站点级（storeId 为空）文章。

#### Scenario: 按门店过滤文章

- GIVEN 站点下有一篇 storeId=null 的文章和一篇 storeId=store_1 的文章
- WHEN 请求列表并指定 `storeId=store_1`
- THEN 两篇文章都出现在结果中

### Requirement: 文章与站点支持软删除与回收站

删除文章 / 站点为软删除（移入回收站），可恢复或永久删除。

#### Scenario: 删除文章后进入回收站

- WHEN 管理员删除一篇文章
- THEN 该文章的 `isDeleted` 为 true
- AND 不出现在正常列表中，但出现在回收站列表中

#### Scenario: 恢复已删除文章

- WHEN 管理员恢复一篇在回收站中的文章
- THEN 该文章的 `isDeleted` 恢复为 false，重新出现在正常列表中

### Requirement: 文章更新必须保留版本快照

更新文章前，系统将更新前的状态写入版本历史表，便于追溯。

#### Scenario: 更新文章生成版本快照

- WHEN 管理员更新一篇文章的标题
- THEN 在 `content_versions` 表中新增一条 `content_type="cms_article"` 的快照记录
- AND 可通过 `GET /api/v1/cms/articles/{id}/versions` 查看历史

### Requirement: Admin 端必须提供站点 / 栏目 / 文章的管理界面

Admin 端在「内容站点」一级菜单下提供站点管理、栏目管理、文章管理三个子模块，并按权限控制可见性与操作。

#### Scenario: 拥有 cms:article 权限的管理员

- WHEN 管理员拥有 `cms:article` 相关权限但无 `cms:site` 权限
- THEN 在菜单中只能看到「文章管理」，看不到「站点管理」
