# LowCode 模块 (低代码搭建)

基于 JSON Schema 的可视化页面搭建模块，支持运营人员通过拖拽物料组件快速搭建营销页、活动页、科室介绍页等非核心业务页面。Schema 存储于 PostgreSQL JSONB 列，通过前端运行时渲染器在 Admin H5、患者小程序中动态渲染。

## 目录结构

```
modules/lowcode/
  __init__.py              # 模块入口，导出 lowcode_router + template_router
  router.py                # 页面 CRUD + 数据绑定 + 代码生成 + 版本管理 + 部署路由
  router_template.py       # 模板市场路由 (10 个端点)
  service.py               # CRUD 业务逻辑 (LowCodePageService)
  codegen_service.py       # 代码生成服务 (subprocess 调用 Node.js codegen 包)
  template_service.py      # 模板市场 CRUD (LowCodeTemplateService)
  version_service.py       # 页面版本快照与回滚 (LowCodePageVersionService)
  feature_gate.py          # 功能门禁 (LowCodeFeatureGate)
  deploy_service.py        # 部署流水线 (LowCodeDeployService)
  schemas.py               # re-export + 模块专属 schemas
```

关联文件:

```
app/models/lowcode_page.py                # SQLAlchemy 模型 (LowCodePage)
app/models/lowcode_page_version.py        # 页面版本历史模型 (LowCodePageVersion)
app/models/lowcode_template.py            # 模板市场模型 (LowCodeTemplate)
app/models/lowcode_template_version.py    # 模板版本 + Fork 模型
app/schemas/lowcode.py                    # Pydantic 请求/响应 schema
app/api/v1/__init__.py                    # 路由注册: /lowcode + /lowcode/templates
packages/shared/src/types/lowcode.ts      # 前端 TypeScript 类型定义
packages/api/src/modules/lowcode.ts       # 前端 API 封装 (lowcodeApi)
packages/codegen/                         # Node.js 代码生成器 (Taro / 原生小程序)
```

## 架构概览

模块分为三层递进式能力:

| 层级 | 能力 | 说明 |
|------|------|------|
| Phase 1 | 基础搭建 | Schema 存储、物料拖拽、预览渲染、CRUD、发布/归档 |
| Phase 2 | 数据绑定 + 代码生成 | 数据源配置、表达式引擎、Taro/原生小程序代码生成 |
| Phase 3 | 平台化 | 功能门禁、版本管理、模板市场、部署流水线、微信审核 |

---

## API 端点 -- 页面管理

基础路径: `/api/v1/lowcode`

所有页面端点需要管理员认证 (`get_current_admin`)，并受 RBAC 权限控制。

### Phase 1 -- 基础 CRUD

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/pages` | `lowcode:page:list` | 分页获取页面列表，支持 status 筛选和 keyword 搜索 |
| POST | `/pages` | `lowcode:page:create` | 创建页面，slug 必须在租户内唯一。受功能门禁 `lowcode_basic` 和页面配额限制 |
| GET | `/pages/{page_id}` | `lowcode:page:read` | 获取页面详情 |
| PUT | `/pages/{page_id}` | `lowcode:page:update` | 更新页面（含 schema、状态等） |
| DELETE | `/pages/{page_id}` | `lowcode:page:delete` | 删除页面（仅草稿状态可删） |
| POST | `/pages/{page_id}/publish` | `lowcode:page:publish` | 发布页面（status 0 -> 1）。若 schema 含 dataBindings，需 `lowcode_advanced_components` |
| POST | `/pages/{page_id}/archive` | `lowcode:page:update` | 归档页面（status 1 -> 2） |

### Phase 2 -- 数据绑定

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/data-sources/test` | `lowcode:page:read` | 沙箱测试数据源配置（超时 5s, 响应最大 1MB），返回响应样本及字段建议 |
| GET | `/pages/{page_id}/data-preview` | `lowcode:page:read` | 基于 schema.dataSources 生成 mock 数据预览（不实际发起网络请求） |

### Phase 2 -- 代码生成

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/pages/{page_id}/codegen/preview` | `lowcode:page:read` | 预览代码生成结果（不持久化），需 `lowcode_codegen` |
| POST | `/pages/{page_id}/codegen/taro` | `lowcode:page:codegen` | 生成 Taro 小程序页面代码，需 `lowcode_codegen` |
| GET | `/pages/{page_id}/codegen/download` | `lowcode:page:codegen` | 下载生成代码的 ZIP 包（支持 taro / native） |

### Phase 3 -- 版本管理

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/pages/{page_id}/versions` | `lowcode:page:read` | 按版本号降序列出页面所有版本记录 |
| POST | `/pages/{page_id}/versions/rollback` | `lowcode:page:update` | 回滚到指定历史版本，回滚操作本身也会生成一条新的版本记录 |

### Phase 3 -- 部署流水线

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/pages/{page_id}/deploy` | `lowcode:page:deploy` | 触发完整部署流水线（codegen -> build -> upload -> audit），需 `lowcode_publish_miniapp` |
| GET | `/pages/{page_id}/deploy-status` | `lowcode:page:read` | 查询部署状态及最近构建任务信息 |
| POST | `/pages/{page_id}/deploy-rollback` | `lowcode:page:deploy` | 回滚到上一个已发布版本 |
| POST | `/pages/{page_id}/preview-deploy` | `lowcode:page:deploy` | 上传代码到微信开发版并生成体验二维码 |
| POST | `/deploy/wechat-audit-callback` | 无（公开回调） | 微信审核状态 Webhook 回调 |

### 列表查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | int | 否 | 状态筛选: 0=草稿, 1=已发布, 2=已归档 |
| keyword | string | 否 | 按页面名称模糊搜索 |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 10，上限由 `MAX_PAGE_SIZE` 配置 |

### 响应格式

遵循系统统一响应格式 `{"code": 0, "message": "success", "data": {...}}`。

列表响应使用 `PageResponse` 包装:

```json
{
  "code": 0,
  "data": {
    "data": [ ... ],
    "total": 25,
    "page": 1,
    "page_size": 10
  }
}
```

单页响应:

```json
{
  "code": 0,
  "data": {
    "id": "uuid",
    "tenant_id": "tenant-uuid",
    "name": "科室介绍页",
    "slug": "dept-intro",
    "description": "骨科科室介绍",
    "schema_data": { ... },
    "status": 0,
    "current_version": 3,
    "publish_count": 2,
    "thumbnail_url": null,
    "miniapp_instance_id": null,
    "deploy_status": "idle",
    "last_deploy_at": null,
    "last_build_job_id": null,
    "created_at": "2026-06-01T10:00:00",
    "updated_at": "2026-06-01T10:00:00"
  }
}
```

---

## API 端点 -- 模板市场

基础路径: `/api/v1/lowcode/templates`

模板市场列表和详情为公开接口（无需认证）。创建、更新、删除、Fork、版本管理需要管理员认证。

### 模板 CRUD

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/templates` | 无（公开） | 获取模板市场列表，支持分类筛选、关键词搜索、排序 |
| GET | `/templates/{template_id}` | 无（公开） | 获取模板详情（含 schema_data 和 data_sources） |
| POST | `/templates` | `lowcode:template:create` | 从已有页面创建模板并发布到市场，需 `lowcode_marketplace` |
| PUT | `/templates/{template_id}` | `lowcode:template:update` | 更新模板元数据（名称、描述、分类等，不修改 schema） |
| DELETE | `/templates/{template_id}` | `lowcode:template:delete` | 软删除模板（status -> 0） |
| GET | `/templates/my` | `lowcode:template:list` | 获取当前租户发布的所有模板 |
| GET | `/templates/categories` | 无（公开） | 获取预定义分类列表及各分类模板数量 |

### 模板 Fork

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/templates/{template_id}/fork` | `lowcode:template:fork` | 基于模板 schema 在当前租户创建新页面，需 `lowcode_basic` |

### 模板版本管理

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/templates/{template_id}/versions` | `lowcode:template:read` | 按版本号降序列出模板所有版本记录 |
| POST | `/templates/{template_id}/versions` | `lowcode:template:update` | 创建模板新版本快照，使用语义化版本号（如 1.1.0） |

### 模板列表查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| category | string | 否 | 分类筛选 |
| keyword | string | 否 | 按名称/描述全文搜索 |
| sort_by | string | 否 | 排序方式: popular(下载量, 默认) / newest(创建时间) / forks(Fork数) |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 10 |

### 预定义分类

预约挂号、健康档案、报告查询、排队叫号、科室导航、健康宣教、满意度调查、其他

---

## Phase 2 -- 数据绑定与表达式引擎

### 数据源配置

页面 schema 中通过 `dataSources` 字段定义远程数据源:

```json
{
  "schema_data": {
    "dataSources": [
      {
        "id": "doctorList",
        "url": "https://api.example.com/doctors",
        "method": "GET",
        "headers": { "Authorization": "Bearer {{token}}" },
        "params": { "department_id": "{{deptId}}" },
        "dataPath": "data.list",
        "polling_interval": 30000
      }
    ]
  }
}
```

### 数据绑定表达式

组件节点通过 `dataBinding` 将属性绑定到数据源:

```json
{
  "id": "node-1",
  "componentName": "NutText",
  "props": { "text": "" },
  "dataBinding": {
    "text": "{{doctorList[0].name}}"
  }
}
```

### State 定义

页面可声明全局状态，供数据绑定引用:

```json
{
  "schema_data": {
    "state": {
      "deptId": { "type": "string", "defaultValue": "1001" },
      "token": { "type": "string", "defaultValue": "" }
    }
  }
}
```

### 数据源测试

调用 `POST /data-sources/test` 在沙箱中测试数据源配置:

- 超时限制: 5 秒
- 响应体最大: 1 MB
- 样本数据列表最多: 5 条
- 返回字段类型建议，供设计器绑定使用

### 数据预览

调用 `GET /pages/{page_id}/data-preview` 基于 schema 定义生成 mock 数据，不实际发起网络请求，供设计器实时预览。

---

## Phase 2 -- 代码生成

代码生成器通过 subprocess 调用 Node.js codegen 包 (`packages/codegen/`)，将低代码 schema 转换为可运行的源代码。

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CODEGEN_BIN` | `<project>/packages/codegen/dist/index.js` | Node.js codegen 入口脚本路径 |
| `CODEGEN_NODE_CMD` | `node` | Node.js 可执行命令 |
| `CODEGEN_TIMEOUT` | `30` | subprocess 超时秒数 |

### 支持的目标平台

| 目标 | 输出文件 | 说明 |
|------|----------|------|
| `taro` | `pages/<slug>/index.tsx` | Taro 框架小程序页面（默认） |
| `native` | `.wxml` / `.wxss` / `.js` / `.json` | 原生微信小程序页面 |

### 代码生成流程

```
Schema JSON -> CodegenService._run_codegen() -> subprocess(node script) -> CodegenResult
```

1. 从 schema 中提取 `children` 组件树、`dataSources`、`state`
2. 写入临时 Node.js 包装脚本
3. 通过 stdin 传递 JSON 输入
4. 解析 stdout JSON 输出为 `CodegenResult`
5. 返回 `GeneratedFile` 列表 + warnings + dependencies + metadata

### 预览与下载

- **预览**: `POST /pages/{page_id}/codegen/preview` -- 前端传入 schema，返回生成文件列表（不落盘）
- **生成**: `POST /pages/{page_id}/codegen/taro` -- 从数据库加载 schema 并生成 Taro 代码
- **下载**: `GET /pages/{page_id}/codegen/download?target=taro` -- 返回 ZIP 压缩包

---

## Phase 3 -- 功能门禁

### LowCodeFeatureGate

功能门禁服务 (`feature_gate.py`) 基于 `FeatureFlagService` 和订阅计划，检查租户是否有权使用指定的低代码功能。

| 功能开关 | 说明 | 触发点 |
|----------|------|--------|
| `lowcode_basic` | 基础低代码功能 | 创建页面、Fork 模板 |
| `lowcode_advanced_components` | 高级组件（含数据绑定） | 发布含 dataBindings 的页面 |
| `lowcode_codegen` | 代码生成 | 代码预览、Taro 生成、ZIP 下载 |
| `lowcode_marketplace` | 模板市场 | 创建模板、发布到市场 |
| `lowcode_publish_miniapp` | 小程序发布 | 部署流水线、预览二维码 |

### 页面配额

`LowCodeFeatureGate.check_page_limit()` 从 `TenantFeatures.lowcode_max_pages` 读取配额上限，超过时抛出 403（`QUOTA_EXCEEDED`）。`max_pages == 0` 表示不限制。

### 错误响应

功能未启用时返回:

```json
{
  "code": 403,
  "message": "当前订阅计划不支持此功能: lowcode_codegen",
  "data": null
}
```

Header 中携带 `X-Error-Code: PERMISSION_DENIED` 或 `X-Error-Code: QUOTA_EXCEEDED`。

---

## Phase 3 -- 版本管理

### 页面版本 (LowCodePageVersion)

每次发布或手动保存时，`LowCodePageVersionService` 自增版本号并生成快照:

| 字段 | 说明 |
|------|------|
| `page_id` | 关联页面 ID |
| `version` | 整数版本号，从 1 递增 |
| `schema_data` | Schema JSONB 快照 |
| `data_sources` | 数据源配置快照 |
| `snapshot_label` | 版本标签（如 "回滚至 v3"） |

版本号由 `page.current_version` 字段跟踪，每次快照或回滚自动 +1。`page.publish_count` 记录总发布次数。

### 回滚机制

回滚到指定版本时:

1. 读取目标版本的 `schema_data`
2. 更新当前页面的 `schema_data`
3. 创建一条新的版本记录（版本号 +1），label 标记为 "回滚至 v{x}"
4. 更新 `page.current_version` 和 `page.publish_count`

回滚操作本身也会记录在版本历史中，可追溯。

---

## Phase 3 -- 模板市场

### 数据模型

| 表 | 说明 |
|----|------|
| `lowcode_templates` | 模板主表，存储 schema、元数据、下载/Fork/收藏计数 |
| `lowcode_template_versions` | 模板版本历史，语义化版本号（如 1.0.0） |
| `lowcode_template_forks` | Fork 记录，追踪谁 fork 了哪个模板 |

### 模板市场工作流

```
1. 创建模板
   运营人员在编辑器中搭建好页面 -> "发布到模板市场"
   -> POST /templates (从页面复制 schema_data)
   -> 模板出现在市场列表

2. 浏览模板
   其他租户浏览市场 -> GET /templates (分类筛选/排序)
   -> 查看模板详情 -> GET /templates/{id} (含完整 schema)

3. Fork 模板
   运维人员选择模板 -> "使用此模板"
   -> POST /templates/{id}/fork
   -> 在当前租户创建新页面 (复制 schema_data)
   -> fork_count +1, download_count +1

4. 模板版本管理
   模板作者修改 schema -> "发布新版本"
   -> POST /templates/{id}/versions (语义化版本号 + schema 快照)
   -> 模板主版本号同步更新

5. 模板元数据管理
   -> PUT /templates/{id} (更新名称/描述/分类/标签/公开状态)
   -> DELETE /templates/{id} (软删除，status -> 0)
```

### 模板预定义分类

预约挂号、健康档案、报告查询、排队叫号、科室导航、健康宣教、满意度调查、其他

---

## Phase 3 -- 部署流水线

### 部署状态机

```
idle -> building -> built -> uploading -> uploaded -> auditing -> published
                                                                    |
  +----failed----+----failed----+----failed----+----failed----+----failed----+
  |              |              |              |              |              |
  +--(可重试)--> building      |              |              |              |
                              |              |              |              |
  published -----------------+              |              |              |
  auditing ------------------+              |              |              |
                                             |              |              |
  任何失败状态 -----(重试)-----> building    |              |              |
```

状态转换规则:

| 当前状态 | 允许转换到 |
|----------|-----------|
| idle | building |
| building | built, failed |
| built | uploading, failed |
| uploading | uploaded, failed |
| uploaded | auditing, failed |
| auditing | published, failed |
| failed | building（重试） |
| published | building（重新构建） |

### 部署流水线工作流

```
1. 触发部署
   POST /pages/{id}/deploy
   -> 创建 BuildJob 记录
   -> 阶段 1: 代码生成 (CodegenService.generate_taro)
   -> 阶段 2: 构建小程序包 (_stage_build, 产物上传到 artifact 存储)
   -> 阶段 3: 上传到微信平台 (wx/commit)
   -> 阶段 4: 提交微信审核 (wx/submit_audit)
   -> 返回 build_job_id + audit_id

2. 查询部署状态
   GET /pages/{id}/deploy-status
   -> 返回 deploy_status, last_deploy_at, 最近 BuildJob 信息

3. 微信审核回调
   POST /deploy/wechat-audit-callback (公开端点，无需认证)
   -> 微信审核完成后调用
   -> 审核通过: deploy_status -> published, page.status -> 1
   -> 审核失败: deploy_status -> failed

4. 部署回滚
   POST /pages/{id}/deploy-rollback
   -> 查询上一个成功的 BuildJob
   -> 创建 ReleaseJob (action=rollback)
   -> deploy_status -> uploaded

5. 预览二维码
   POST /pages/{id}/preview-deploy
   -> 上传代码到微信开发版
   -> 返回体验二维码 URL 供测试人员扫码预览
```

### 部署前置条件

- 页面必须已关联小程序实例 (`miniapp_instance_id` 非空)
- 租户必须启用 `lowcode_publish_miniapp` 功能开关
- 当前部署状态必须允许转换（遵循状态机规则）

### BuildJob 模型

| 字段 | 说明 |
|------|------|
| `tenant_id` | 租户 ID |
| `miniapp_instance_id` | 小程序实例 ID |
| `lowcode_page_id` | 低代码页面 ID |
| `trigger_source` | 触发来源（如 "lowcode_deploy"） |
| `status` | pending / completed / failed |
| `artifact_url` | 构建产物 URL |
| `build_log` | 构建日志 |
| `started_at` / `finished_at` | 开始/结束时间 |

---

## Schema DSL

`schema_data` 字段存储一棵组件树，使用 JSONB 格式持久化。树的结构由 `LowCodeSchema` (根节点) 和 `LowCodeNode` (子节点) 定义。

### 根节点 (LowCodeSchema)

```typescript
interface LowCodeSchema {
  componentName: 'Page';        // 固定为 Page
  props: {
    navigationBarTitleText: string;           // 导航栏标题
    navigationBarBackgroundColor: string;     // 导航栏背景色
    navigationBarTextStyle: 'black' | 'white'; // 导航栏文字颜色
  };
  children: LowCodeNode[];      // 子组件列表
  dataSources?: DataSource[];   // 数据源配置 (Phase 2)
  state?: Record<string, StateDef>; // 全局状态定义 (Phase 2)
  dataBinding?: Record<string, string>; // 根级数据绑定 (Phase 2)
}
```

### 组件节点 (LowCodeNode)

```typescript
interface LowCodeNode {
  id: string;                    // 唯一标识 (UUID)
  componentName: string;         // 组件名，如 NutText, NutView
  props: Record<string, any>;    // 组件属性
  children?: LowCodeNode[];      // 子节点（容器组件）
  dataBinding?: Record<string, string>; // 数据绑定表达式
  visible?: string;              // 条件显示表达式 (如 "list.length > 0")
}
```

### Schema 校验规则

服务端 Pydantic schema 在写入时校验:

1. **嵌套深度限制**: 最大 10 层，防止过深嵌套
2. **结构校验**: 每个节点必须包含 `componentName` (string) 和 `props` (object)
3. **children 校验**: 如果存在，必须是数组，递归校验每个子节点

### 示例 Schema

```json
{
  "componentName": "Page",
  "props": {
    "navigationBarTitleText": "骨科介绍",
    "navigationBarBackgroundColor": "#ffffff",
    "navigationBarTextStyle": "black"
  },
  "state": {
    "deptId": { "type": "string", "defaultValue": "1001" }
  },
  "dataSources": [
    {
      "id": "doctorList",
      "url": "https://api.example.com/doctors",
      "method": "GET",
      "params": { "department_id": "{{deptId}}" },
      "dataPath": "data.list"
    }
  ],
  "children": [
    {
      "id": "a1b2c3",
      "componentName": "NutSwiper",
      "props": { "autoPlay": 3000, "loop": true, "height": "200px" },
      "children": [
        {
          "id": "d4e5f6",
          "componentName": "NutSwiperItem",
          "props": {},
          "children": [
            {
              "id": "g7h8i9",
              "componentName": "NutImage",
              "props": { "src": "https://example.com/banner1.jpg", "width": "100%", "height": "200px", "fit": "cover" },
              "children": []
            }
          ]
        }
      ]
    },
    {
      "id": "j1k2l3",
      "componentName": "NutText",
      "props": { "text": "", "fontSize": "20px", "fontWeight": "bold", "color": "#333333" },
      "dataBinding": {
        "text": "{{doctorList[0].name}}"
      },
      "children": []
    }
  ]
}
```

---

## 数据模型

### lowcode_pages 表

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | varchar(36) | PK, UUID | 主键 |
| tenant_id | varchar(36) | FK -> tenants.id, NOT NULL, INDEX | 租户 ID |
| name | varchar(100) | NOT NULL | 页面名称 |
| slug | varchar(100) | NOT NULL | 页面标识，租户内唯一 |
| description | varchar(500) | NULLABLE | 页面描述 |
| schema_data | JSONB | NOT NULL, default '{}' | 页面 Schema JSON |
| status | int | default 0 | 状态: 0=草稿, 1=已发布, 2=已归档 |
| current_version | int | default 0 | 当前版本号 |
| publish_count | int | default 0 | 发布次数 |
| thumbnail_url | varchar(500) | NULLABLE | 缩略图 URL |
| miniapp_instance_id | varchar(36) | FK -> miniapp_instances.id, NULLABLE, INDEX | 关联小程序实例 |
| deploy_status | varchar(30) | NOT NULL, default 'idle' | 部署状态 |
| last_deploy_at | timestamp | NULLABLE | 最近部署时间 |
| last_build_job_id | varchar(36) | FK -> build_jobs.id, NULLABLE, INDEX | 最近构建任务 ID |
| created_at | timestamp | | 创建时间 (AuditMixin) |
| updated_at | timestamp | | 更新时间 (AuditMixin) |
| created_by | varchar(100) | | 创建人 (AuditMixin) |
| updated_by | varchar(100) | | 更新人 (AuditMixin) |

唯一约束: `(tenant_id, slug)` -- `uq_lowcode_pages_tenant_slug`

### lowcode_page_versions 表

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | varchar(36) | PK, UUID | 主键 |
| page_id | varchar(36) | FK -> lowcode_pages.id, CASCADE, INDEX | 页面 ID |
| tenant_id | varchar(36) | FK -> tenants.id, CASCADE, INDEX | 租户 ID |
| version | int | NOT NULL | 版本号，从 1 递增 |
| schema_data | JSONB | NOT NULL | Schema 快照 |
| data_sources | JSONB | NOT NULL, default [] | 数据源配置快照 |
| snapshot_label | varchar(200) | NULLABLE | 版本标签 |
| created_by | varchar(36) | FK -> accounts.id, NULLABLE | 创建人 |
| created_at | timestamp | | 创建时间 (AuditMixin) |

唯一约束: `(page_id, version)` -- `uq_lowcode_page_versions_page_version`

### lowcode_templates 表

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | varchar(36) | PK, UUID | 主键 |
| source_page_id | varchar(36) | FK -> lowcode_pages.id, NULLABLE, INDEX, UNIQUE | 来源页面 ID |
| source_tenant_id | varchar(36) | FK -> tenants.id, NOT NULL, INDEX | 来源租户 ID |
| name | varchar(200) | NOT NULL | 模板名称 |
| description | text | NULLABLE | 模板描述 |
| thumbnail_url | varchar(500) | NULLABLE | 缩略图 URL |
| category | varchar(50) | NOT NULL, INDEX | 模板分类 |
| tags | JSONB | NULLABLE, default [] | 标签列表 |
| schema_data | JSONB | NOT NULL | 模板 Schema JSON |
| data_sources | JSONB | NULLABLE, default [] | 数据源配置 |
| version | varchar(20) | NOT NULL, default '1.0.0' | 当前版本 |
| is_public | bool | NOT NULL, default False | 是否公开 |
| is_official | bool | NOT NULL, default False | 是否官方 |
| download_count | int | NOT NULL, default 0 | 下载次数 |
| fork_count | int | NOT NULL, default 0 | Fork 次数 |
| like_count | int | NOT NULL, default 0 | 收藏次数 |
| status | int | NOT NULL, default 1 | 状态: 0=禁用, 1=正常 |
| created_by | varchar(36) | FK -> accounts.id, INDEX | 创建人 |
| created_at / updated_at | timestamp | | 时间戳 (AuditMixin) |

### lowcode_template_versions 表

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | varchar(36) | PK, UUID | 主键 |
| template_id | varchar(36) | FK -> lowcode_templates.id, CASCADE, INDEX | 模板 ID |
| version | varchar(20) | NOT NULL | 语义化版本号 |
| schema_data | JSONB | NOT NULL | Schema 快照 |
| data_sources | JSONB | NOT NULL, default {} | 数据源配置快照 |
| changelog | text | NULLABLE | 变更说明 |
| status | int | NOT NULL, default 1 | 版本状态: 1=草稿, 2=已发布, 3=已废弃 |
| created_by | varchar(36) | FK -> accounts.id, NULLABLE | 创建人 |
| created_at | timestamp | | 创建时间 (AuditMixin) |

唯一约束: `(template_id, version)` -- `uq_lowcode_template_versions_template_version`

### lowcode_template_forks 表

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | varchar(36) | PK, UUID | 主键 |
| original_template_id | varchar(36) | FK -> lowcode_templates.id, CASCADE, INDEX | 原始模板 ID |
| forked_page_id | varchar(36) | FK -> lowcode_pages.id, SET NULL | Fork 生成的页面 ID |
| forked_by_tenant_id | varchar(36) | FK -> tenants.id, CASCADE, INDEX | Fork 操作的租户 ID |
| forked_by_account_id | varchar(36) | FK -> accounts.id, NOT NULL | Fork 操作的账号 ID |
| created_at | int | NOT NULL | Fork 时间戳（秒级 Unix） |

### 页面状态机

```
草稿 (0) --发布--> 已发布 (1) --归档--> 已归档 (2)
                   |
                   +--删除--> (仅草稿状态可删)
```

- 草稿 -> 已发布: POST `/pages/{id}/publish`
- 已发布 -> 已归档: POST `/pages/{id}/archive`
- 删除: DELETE `/pages/{id}` (仅 status=0 时允许)

### 部署状态机

```
idle -> building -> built -> uploading -> uploaded -> auditing -> published
  ^                                                           |
  +------(重试/重新构建)------ failed <-----------------------+
```

---

## 物料 (MaterialComponent)

物料是编辑器左侧面板中可拖拽的预定义组件。每个物料定义了组件名、默认属性和属性面板配置。

### 物料注册

物料定义在 `apps/admin/src/pages/lowcode/editor/materials/` 目录下，按分类组织:

```
materials/
  index.ts      # 物料注册表，导出 allMaterials, materialsByCategory, findMaterial
  basic.tsx     # 基础物料: NutText, NutImage, NutButton, NutDivider
  layout.tsx    # 布局物料: NutView, NutRow, NutCol
  display.tsx   # 展示物料: NutSwiper, NutSwiperItem, NutCell, NutCard, NutTabs, NutTabPane, NutEmpty
```

### 物料类型定义

```typescript
interface MaterialComponent {
  componentName: string;     // 组件名，如 'NutText'
  title: string;             // 显示名称，如 '文本'
  icon: string;              // Ant Design 图标名
  category: 'basic' | 'layout' | 'display' | 'form' | 'business';
  defaultProps: Record<string, any>;   // 拖入画布时的默认属性
  configureSchema: PropertyConfig[];   // 属性面板配置
}
```

### 属性配置项 (PropertyConfig)

```typescript
interface PropertyConfig {
  key: string;              // 属性名
  label: string;            // 显示标签
  type: 'input' | 'number' | 'select' | 'color' | 'switch' | 'textarea' | 'image';
  defaultValue?: any;       // 默认值
  options?: { label: string; value: any }[];  // select 类型的选项
  placeholder?: string;     // 输入框占位文字
}
```

### 当前可用物料清单

| 分类 | 组件名 | 说明 |
|------|--------|------|
| **基础** | NutText | 文本，支持字号/颜色/字重/对齐 |
| | NutImage | 图片，支持 URL/尺寸/填充模式/圆角 |
| | NutButton | 按钮，支持类型/块级/禁用 |
| | NutDivider | 分割线，支持虚线/位置 |
| **布局** | NutView | 布局容器，支持边距/背景色/圆角 |
| | NutRow | 栅格行，支持间距/排列/对齐 |
| | NutCol | 栅格列，支持 24 栏宽度 |
| **展示** | NutSwiper | 轮播，支持自动播放/循环/指示器 |
| | NutSwiperItem | 轮播项 (子组件) |
| | NutCell | 单元格，支持标题/描述/箭头 |
| | NutCard | 卡片，支持标题/副标题/描述 |
| | NutTabs | 标签页容器 |
| | NutTabPane | 标签面板 (子组件) |
| | NutEmpty | 空状态提示 |

### 添加新物料

1. 在 `materials/` 对应分类文件 (或新建文件) 中定义 `MaterialComponent` 数组:

```typescript
// materials/form.tsx
import type { MaterialComponent } from '@hospital/shared';

export const formMaterials: MaterialComponent[] = [
  {
    componentName: 'NutInput',
    title: '输入框',
    icon: 'EditOutlined',
    category: 'form',
    defaultProps: {
      placeholder: '请输入',
      border: true,
    },
    configureSchema: [
      { key: 'placeholder', label: '占位文字', type: 'input', defaultValue: '请输入' },
      { key: 'border', label: '显示边框', type: 'switch', defaultValue: true },
    ],
  },
];
```

2. 在 `materials/index.ts` 中注册:

```typescript
import { formMaterials } from './form';

export const allMaterials: MaterialComponent[] = [
  ...basicMaterials,
  ...layoutMaterials,
  ...displayMaterials,
  ...formMaterials,       // 新增
];

export const materialsByCategory = {
  basic: basicMaterials,
  layout: layoutMaterials,
  display: displayMaterials,
  form: formMaterials,    // 新增
};
```

3. 在 `SchemaRenderer.tsx` 和 `LowCodeRenderer` (小程序) 中添加对应的渲染分支。

## 业务规则

- 所有页面数据按租户隔离，查询和操作均需携带 `tenant_id`
- `slug` 在同一租户内唯一，创建和更新时会自动校验
- 中文名称可通过前端 pinyin 库自动转换为 slug
- 仅草稿状态 (status=0) 的页面可删除
- 发布/归档操作会自动设置对应的 status 值
- 删除操作为物理删除 (非软删除)
- 功能门禁基于订阅计划控制，低级计划无法使用代码生成、模板市场、小程序发布等高级功能
- 模板市场列表和详情为公开接口，无需认证即可浏览
- 模板 Fork 会在当前租户创建独立副本，与原模板无后续关联
- 部署流水线需要页面已关联小程序实例
- 微信审核回调为公开端点（TODO: 接入时需增加签名校验）

## 测试

单元测试文件: `tests/unit/test_lowcode_page.py`

```bash
cd apps/server
pytest tests/unit/test_lowcode_page.py -v
```
