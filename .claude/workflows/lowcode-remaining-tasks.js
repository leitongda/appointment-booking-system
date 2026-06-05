export const meta = {
  name: 'lowcode-remaining-tasks',
  description: '修复低代码模块剩余问题：Bug修复、测试补充、编辑器增强、组件扩充、模板市场、代码质量、类型补全',
  phases: [
    { title: 'Bug Fixes', detail: '修复4个必须修复的Bug和安全漏洞' },
    { title: 'Unit Tests', detail: '补充codegen_service/deploy_service/miniapp_publisher/schemas测试' },
    { title: 'Editor UX', detail: '图层面板、快捷键、拖拽精度、画布缩放' },
    { title: 'Components', detail: '扩充NutUI组件库' },
    { title: 'Marketplace', detail: '模板市场接入真实API、清理死代码' },
    { title: 'Code Quality', detail: '提取重复函数、修复数据源存储不一致' },
    { title: 'TypeScript', detail: '补全DeployStatus/BuildJob/ReleaseJob类型' },
    { title: 'Verify', detail: '运行测试验证所有变更' },
  ],
};

// ============================================================
// Phase 1: Bug Fixes — 必须修复
// ============================================================
phase('Bug Fixes');

const bugFixes = await agent(
  `修复低代码模块的4个必须修复的问题。请逐个处理：

1. **miniapp_publisher.py submit_audit 用GET而非POST**
   文件: apps/server/app/infrastructure/wechat/miniapp_publisher.py
   问题: submit_audit 方法使用 client.get() 而非 client.post()
   修复: 将 client.get(url, params=data) 改为 client.post(url, json=data)
   参考微信文档: POST https://api.weixin.qq.com/wxa/submit_audit

2. **lowcode_deploy_task.py tar.extractall 无路径穿越保护**
   文件: apps/server/app/tasks/lowcode_deploy_task.py
   问题: _extract_artifact 函数使用 tar.extractall() 无安全过滤
   修复: 使用 Python 3.12+ 的 tar.extractall(filter='data') 或手动验证每个成员路径不包含 '..'

3. **lowcode_deploy_task.py 临时目录从不清理**
   文件: apps/server/app/tasks/lowcode_deploy_task.py
   问题: tempfile.mkdtemp() 创建的目录从不清理
   修复: 在每个 task 的 finally 块中添加 shutil.rmtree(temp_dir, ignore_errors=True)

4. **lowcode_deploy_task.py rollback_task 的 target_version 参数被忽略**
   文件: apps/server/app/tasks/lowcode_deploy_task.py
   问题: rollback_task 接受 target_version 参数但从未使用
   修复: 如果 target_version 不为 None，回滚到指定版本；否则回滚到上一个版本

请先 Read 每个文件，理解上下文，然后做最小化的精确修改。不要改变其他逻辑。`,
  { label: 'fix:bugs', phase: 'Bug Fixes', isolation: 'worktree' }
);

// ============================================================
// Phase 2: Unit Tests — 补充核心模块测试
// ============================================================
phase('Unit Tests');

const testFiles = await parallel([
  () => agent(
    `为 codegen_service.py 编写单元测试。
    文件: apps/server/app/modules/lowcode/codegen_service.py
    测试文件: apps/server/tests/unit/test_lowcode_codegen.py

    先 Read codegen_service.py 理解所有公开方法，然后编写测试：
    - test_generate_taro_page: 测试基本页面代码生成
    - test_generate_taro_component: 测试组件代码生成
    - test_generate_with_data_binding: 测试数据绑定表达式生成
    - test_generate_with_events: 测试事件处理代码生成
    - test_generate_with_loop: 测试循环渲染代码生成
    - test_invalid_schema: 测试无效 schema 的错误处理
    - test_empty_schema: 测试空 schema 的边界情况

    使用 pytest + pytest-asyncio，参考现有测试文件的 fixtures 风格。
    先 Read apps/server/tests/conftest.py 了解可用 fixtures。`,
    { label: 'test:codegen', phase: 'Unit Tests', isolation: 'worktree' }
  ),
  () => agent(
    `为 deploy_service.py 编写单元测试。
    文件: apps/server/app/modules/lowcode/deploy_service.py
    测试文件: apps/server/tests/unit/test_lowcode_deploy_service.py

    先 Read deploy_service.py 理解所有公开方法，然后编写测试：
    - test_start_deploy: 测试部署触发
    - test_get_deploy_status: 测试状态查询
    - test_cancel_deploy: 测试部署取消
    - test_deploy_with_feature_disabled: 测试功能关闭时的拦截
    - test_deploy_page_not_found: 测试页面不存在
    - test_concurrent_deploy_guard: 测试并发部署保护

    mock Celery task 的.delay() 调用。使用 pytest + pytest-asyncio。`,
    { label: 'test:deploy-service', phase: 'Unit Tests', isolation: 'worktree' }
  ),
  () => agent(
    `为 miniapp_publisher.py 编写单元测试。
    文件: apps/server/app/infrastructure/wechat/miniapp_publisher.py
    测试文件: apps/server/tests/unit/test_lowcode_miniapp_publisher.py

    先 Read miniapp_publisher.py 理解所有方法，然后编写测试：
    - test_upload_code: mock httpx.post 测试代码上传
    - test_submit_audit: mock httpx.post 测试提审
    - test_get_audit_status: mock httpx.get 测试审核状态查询
    - test_release: mock httpx.post 测试发布
    - test_get_preview_qrcode: mock httpx.post 测试预览码
    - test_rollback: mock httpx.post 测试回滚
    - test_token_error: 测试 token 获取失败
    - test_api_error_response: 测试微信 API 返回错误

    mock WechatTokenManager 和 httpx 客户端。使用 pytest。`,
    { label: 'test:publisher', phase: 'Unit Tests', isolation: 'worktree' }
  ),
  () => agent(
    `为 lowcode schemas 编写单元测试。
    文件: apps/server/app/modules/lowcode/schemas.py
    测试文件: apps/server/tests/unit/test_lowcode_schemas.py

    先 Read schemas.py 理解所有 Pydantic model，然后编写测试：
    - test_page_create_valid: 测试有效页面创建数据
    - test_page_create_invalid_slug: 测试无效 slug 格式
    - test_page_update_partial: 测试部分更新
    - test_schema_data_validation: 测试 schema 数据结构校验
    - test_template_create: 测试模板创建
    - test_deploy_request: 测试部署请求
    - test_version_list_params: 测试版本列表参数
    - test_page_list_params_filter: 测试列表过滤参数

    使用 pytest + pydantic ValidationError。`,
    { label: 'test:schemas', phase: 'Unit Tests', isolation: 'worktree' }
  ),
]);

// ============================================================
// Phase 3: Editor UX — 编辑器体验提升
// ============================================================
phase('Editor UX');

const editorUX = await parallel([
  () => agent(
    `为低代码编辑器添加图层面板（Layer Panel）。
    新建文件: apps/admin/src/pages/lowcode/editor/components/LayerPanel.tsx

    功能要求：
    1. 树形结构展示组件层级关系（递归渲染 Schema 节点树）
    2. 每个节点显示组件类型名称和可选的 title/label
    3. 点击节点选中对应组件（调用 store.selectNode）
    4. 选中节点高亮（与画布联动）
    5. 节点可折叠/展开子节点
    6. 支持拖拽重排序（使用 @dnd-kit/sortable）
    7. 删除按钮（调用 store.removeNode）
    8. 显示/隐藏切换（visibility toggle）
    9. 组件类型图标（可选）

    参考现有组件风格，使用 Ant Design 的 Tree 组件或自定义递归组件。
    先 Read editor/store.ts 了解 store 接口，Read editor/components/SchemaRenderer.tsx 了解节点结构。`,
    { label: 'editor:layer-panel', phase: 'Editor UX', isolation: 'worktree' }
  ),
  () => agent(
    `为低代码编辑器完善键盘快捷键。
    修改文件: apps/admin/src/pages/lowcode/editor/index.tsx

    在现有快捷键基础上增加：
    1. Delete / Backspace — 删除选中组件（调用 store.removeNode(selectedId)）
    2. Ctrl+C — 复制选中组件到剪贴板（JSON 序列化）
    3. Ctrl+V — 粘贴组件（从剪贴板反序列化，添加到选中节点的父节点）
    4. Ctrl+D — 复制选中组件（原位复制，偏移 10px）
    5. Ctrl+A — 全选（暂不实现，alert 提示）
    6. 方向键 — 微调选中组件位置（每按一次移动 1px，Shift+方向键移动 10px）

    先 Read editor/index.tsx 理解现有快捷键实现（useEffect + keydown 监听）。
    剪贴板使用 navigator.clipboard.writeText/readText。
    确保不与浏览器默认快捷键冲突（Ctrl+C/V 在没有选中组件时走浏览器默认）。`,
    { label: 'editor:shortcuts', phase: 'Editor UX', isolation: 'worktree' }
  ),
  () => agent(
    `改进低代码编辑器的拖拽插入位置精度。
    修改文件: apps/admin/src/pages/lowcode/editor/components/Canvas.tsx

    当前问题：拖拽只能放到容器末尾（始终使用 parentNode.children.length 作为插入索引）。
    需要改为基于鼠标位置的精确插入。

    实现方案：
    1. 在 dragover 事件中，判断鼠标在目标容器中的 Y 坐标
    2. 遍历容器的子节点 DOM 元素，找到鼠标位置上方最近的兄弟节点
    3. 将新组件插入到该兄弟节点之后（而非末尾）
    4. 添加插入位置指示器（一条蓝色横线显示将要插入的位置）

    先 Read Canvas.tsx 理解现有的 dnd-kit 实现。
    使用 @dnd-kit 的 onDragOver 或自定义 drop indicator 逻辑。`,
    { label: 'editor:drag-precision', phase: 'Editor UX', isolation: 'worktree' }
  ),
]);

// ============================================================
// Phase 4: Components — 扩充组件库
// ============================================================
phase('Components');

const componentExpansion = await agent(
  `扩充低代码编辑器的 NutUI 组件库。从 19 个扩展到 30+ 个。

修改文件: apps/admin/src/pages/lowcode/editor/materials/

需要新增的组件（按优先级）：

1. materials/form.tsx 中新增：
   - NutCheckbox: 复选框，props: checked, label, disabled, onChange
   - NutRadio: 单选框，props: value, label, disabled, onChange
   - NutDatePicker: 日期选择器，props: placeholder, format, mode, onChange
   - NutCalendar: 日历，props: type, startDate, endDate, onSelected

2. materials/display.tsx 中新增：
   - NutIcon: 图标，props: name, size, color
   - NutTag: 标签，props: type, text, color
   - NutAvatar: 头像，props: size, src, text
   - NutBadge: 徽标，props: value, hidden
   - NutProgress: 进度条，props: percent, status, strokeWidth

3. materials/basic.tsx 中新增：
   - NutSearchBar: 搜索栏，props: placeholder, value, onSearch
   - NutNavBar: 导航栏，props: title, leftShow, onBack

每个组件需要：
- 定义 NutComponent 接口（与现有组件风格一致）
- 注册到 materials/index.ts 的 allMaterials 数组
- 确保 SchemaRenderer.tsx 能渲染新增组件（如果需要，修改 SchemaRenderer）

先 Read materials/basic.tsx 和 materials/form.tsx 了解现有组件定义格式。
先 Read SchemaRenderer.tsx 了解渲染逻辑。`,
  { label: 'expand:components', phase: 'Components', isolation: 'worktree'
});

// ============================================================
// Phase 5: Marketplace — 模板市场修复
// ============================================================
phase('Marketplace');

const marketplaceFix = await agent(
  `修复低代码模板市场的问题。

任务清单：

1. **清理重复代码**: 删除 marketplace/TemplateDetail.tsx（MOCK 数据版本），保留 marketplace/detail.tsx（真实 API 版本）。
   确认路由配置指向 detail.tsx。

2. **marketplace/index.tsx 接入真实 API**: 将 MOCK_TEMPLATES 替换为 lowcodeApi.getTemplates() 调用。
   修改文件: apps/admin/src/pages/lowcode/marketplace/index.tsx
   - 使用 ProTable 或 useState + useEffect 调用 API
   - 保持现有的分类筛选、搜索、排序功能
   - 加载状态和错误处理

3. **marketplace/detail.tsx 补全功能**:
   - 添加收藏按钮（调用低代码 API 的收藏端点，如果不存在则添加）
   - 添加使用次数统计展示

先 Read apps/admin/src/pages/lowcode/marketplace/ 下的所有文件。
先 Read packages/api/src/modules/lowcode-template.ts 了解可用的 API 方法。`,
  { label: 'fix:marketplace', phase: 'Marketplace', isolation: 'worktree'
});

// ============================================================
// Phase 6: Code Quality — 代码质量改进
// ============================================================
phase('Code Quality');

const codeQuality = await agent(
  `改进低代码编辑器的代码质量，消除重复代码。

任务清单：

1. **提取共享的节点查找函数**:
   新建文件: apps/admin/src/pages/lowcode/editor/utils/tree.ts
   导出以下函数（从 Canvas.tsx 和 PropertyPanel.tsx 中提取）：
   - findNodeById(nodes, id) — 递归查找节点
   - isDescendant(nodes, ancestorId, descendantId) — 判断是否为后代
   - findParentNode(nodes, childId) — 查找父节点
   然后更新 Canvas.tsx、PropertyPanel.tsx、EventConfig.tsx 使用共享函数。

2. **修复数据源存储不一致**:
   问题: DataSourcePanel 将数据源存到 schema.dataSources，而 store 有独立的 dataSources 状态。
   方案: 统一使用 store 的 dataSources 状态，DataSourcePanel 通过 store.addDataSource/updateDataSource 操作。
   修改: editor/components/DataSourcePanel.tsx

3. **优化 isDirty 检测**:
   问题: JSON.stringify 比较性能差且对属性顺序敏感。
   方案: 使用深度比较函数（如 lodash isEqual）或维护 schema 的 hash 值。
   修改: editor/index.tsx

先 Read 相关文件理解现有实现。`,
  { label: 'improve:code-quality', phase: 'Code Quality', isolation: 'worktree'
});

// ============================================================
// Phase 7: TypeScript — 类型补全
// ============================================================
phase('TypeScript');

const typeCompletion = await agent(
  `补全低代码模块的 TypeScript 类型定义。

修改文件: packages/shared/src/types/lowcode.ts

需要新增/修改的类型：

1. **DeployStatus 联合类型**:
   type DeployStatus = 'idle' | 'building' | 'built' | 'uploading' | 'uploaded' | 'auditing' | 'published' | 'failed';

2. **BuildJob 接口**:
   interface BuildJob {
     id: string;
     pageId: string;
     status: DeployStatus;
     buildLog?: string;
     artifactUrl?: string;
     startedAt?: string;
     finishedAt?: string;
     triggerSource?: string;
   }

3. **ReleaseJob 接口**:
   interface ReleaseJob {
     id: string;
     buildJobId: string;
     version: number;
     status: 'pending' | 'released' | 'rolled_back';
     releasedAt?: string;
   }

4. **PageVersion 接口**（对应服务端 LowCodePageVersion）:
   interface PageVersion {
     id: string;
     pageId: string;
     version: number;
     schemaData: LowCodeSchema;
     changeDescription?: string;
     createdBy?: string;
     createdAt: string;
   }

5. **收紧 LowCodePageCreateData.schemaData 类型**:
   将 schemaData: Record<string, any> 改为 schemaData: LowCodeSchema

6. **扩展 PropertyConfig.type**:
   添加 'date' | 'slider' | 'radio' | 'checkbox' | 'icon' | 'json'

7. **扩展 DataSourceBase**:
   添加 type: 'api' | 'static' | 'mock' 的判别联合

先 Read packages/shared/src/types/lowcode.ts 了解现有类型定义。`,
  { label: 'types:completion', phase: 'TypeScript', isolation: 'worktree'
});

// ============================================================
// Phase 8: Verify — 验证所有变更
// ============================================================
phase('Verify');

const verify = await agent(
  `运行所有低代码相关的测试并报告结果。

步骤：
1. 后端单元测试:
   cd apps/server && python -m pytest tests/unit/test_lowcode_page.py tests/unit/test_lowcode_feature_gate.py tests/unit/test_lowcode_version.py tests/unit/test_lowcode_template.py tests/unit/test_lowcode_deploy.py tests/unit/test_lowcode_codegen.py tests/unit/test_lowcode_deploy_service.py tests/unit/test_lowcode_miniapp_publisher.py tests/unit/test_lowcode_schemas.py -v 2>&1 | tail -60

2. 前端类型检查:
   cd packages/shared && npx tsc --noEmit 2>&1 | tail -20

3. 汇总结果: 报告通过/失败的测试数量，列出所有失败的测试名和错误信息。`,
  { label: 'verify:all', phase: 'Verify' }
);

log('All remaining tasks completed');
return {
  bugFixes,
  testFiles,
  editorUX,
  componentExpansion,
  marketplaceFix,
  codeQuality,
  typeCompletion,
  verify,
};
