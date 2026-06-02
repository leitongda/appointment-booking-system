# LowCode 编辑器 (Admin 端)

基于拖拽的可视化页面搭建编辑器，允许运营人员无需编码即可搭建营销页、活动页、科室介绍页等。编辑器生成的 JSON Schema 存储到后端，通过运行时渲染器在 Admin H5 和患者小程序中动态展示。

## 目录结构

```
pages/lowcode/
  list.tsx                          # 页面管理列表 (ProTable)
  preview.tsx                       # 页面预览 (多设备尺寸)
  editor/
    index.tsx                       # 编辑器主页面 (工具栏 + 三栏布局)
    store.ts                        # Zustand 状态管理 (Schema 操作 + 撤销重做)
    materials/
      index.ts                      # 物料注册表
      basic.tsx                     # 基础物料: NutText, NutImage, NutButton, NutDivider
      layout.tsx                    # 布局物料: NutView, NutRow, NutCol
      display.tsx                   # 展示物料: NutSwiper, NutCell, NutCard, NutTabs 等
    components/
      ComponentPanel.tsx            # 左侧物料面板 (可拖拽组件列表)
      Canvas.tsx                    # 中间画布区域 (拖拽容器 + 渲染)
      SchemaRenderer.tsx            # Schema -> React 组件渲染器 (编辑态)
      PropertyPanel.tsx             # 右侧属性面板 (选中组件的属性编辑)
    __tests__/
      store.test.ts                 # Store 单元测试
```

## 编辑器使用指南

### 进入编辑器

1. 在低代码页面管理列表 (`/platform/lowcode/list`) 点击 **新建页面** -> 进入编辑器 (URL: `/platform/lowcode/editor/new`)
2. 点击已有页面的 **编辑** 按钮 -> 进入编辑器 (URL: `/platform/lowcode/editor/{pageId}`)

### 编辑器布局

编辑器采用三栏布局，占据整个视口高度:

```
+--[ 顶部工具栏 ]----------------------------------------------------------+
|  [返回] 页面搭建                    [撤销] [重做] [预览] [保存] [发布]    |
+--[ 左侧物料面板 ]--+--[ 中间画布 ]---------+--[ 右侧属性面板 ]----------+
|  搜索组件           |                       |                            |
|  > 基础 (4)        |   375x667 模拟手机     |  选择一个组件查看属性        |
|    NutText          |   画布区域             |  -- 或 --                  |
|    NutImage         |                       |  节点ID: xxx               |
|    NutButton        |                       |  [属性表单]                 |
|    NutDivider       |                       |  [删除]                     |
|  > 布局 (3)        |                       |                            |
|    NutView          |                       |                            |
|    NutRow           |                       |                            |
|    NutCol           |                       |                            |
|  > 展示 (7)        |                       |                            |
|    NutSwiper        |                       |                            |
|    ...              |                       |                            |
+--------------------+-----------------------+----------------------------+
```

### 基本操作流程

1. **添加组件**: 从左侧面板拖拽物料到中间画布的放置区域（虚线蓝色边框提示）
2. **选中组件**: 在画布中点击任意组件，右侧属性面板显示该组件的可配置属性
3. **编辑属性**: 在右侧属性面板修改值，画布实时预览效果
4. **重排序**: 在画布内拖拽已有组件到新的位置（蓝色虚线高亮表示放置目标）
5. **删除组件**: 在属性面板底部点击红色 **删除** 链接
6. **保存**: 点击工具栏 **保存** 按钮 (Ctrl+S)，首次保存需填写页面名称和标识
7. **发布**: 点击工具栏 **发布** 按钮，自动先保存再发布
8. **预览**: 点击工具栏 **预览** 按钮，在新标签页中查看效果

### 键盘快捷键

| 快捷键 | 操作 |
|--------|------|
| Ctrl+Z / Cmd+Z | 撤销 |
| Ctrl+Shift+Z / Cmd+Shift+Z | 重做 |
| Ctrl+S / Cmd+S | 保存 |

### 未保存更改保护

- 浏览器关闭/刷新时弹出原生确认对话框
- 路由切换时弹出自定义确认弹窗，提供 **保存并离开** 和 **不保存直接离开** 两个选项

## 物料系统

### 物料分类

| 分类 | 中文名 | 包含组件 |
|------|--------|----------|
| basic | 基础 | NutText, NutImage, NutButton, NutDivider |
| layout | 布局 | NutView, NutRow, NutCol |
| display | 展示 | NutSwiper, NutSwiperItem, NutCell, NutCard, NutTabs, NutTabPane, NutEmpty |
| form | 表单 | (预留，待添加) |
| business | 业务 | (预留，待添加) |

### 物料定义结构

每个物料是一个 `MaterialComponent` 对象:

```typescript
{
  componentName: 'NutText',     // 组件名，对应 Schema 中的 componentName
  title: '文本',                 // 左侧面板显示名
  icon: 'FontSizeOutlined',     // Ant Design 图标名
  category: 'basic',            // 分类
  defaultProps: {                // 拖入画布时的默认 props
    text: '文本内容',
    fontSize: '14px',
    color: '#333333',
    fontWeight: 'normal',
    textAlign: 'left',
  },
  configureSchema: [            // 属性面板配置项
    { key: 'text', label: '文本内容', type: 'textarea' },
    { key: 'fontSize', label: '字号', type: 'input', defaultValue: '14px' },
    { key: 'color', label: '颜色', type: 'color', defaultValue: '#333333' },
    { key: 'fontWeight', label: '字重', type: 'select', options: [...] },
    { key: 'textAlign', label: '对齐', type: 'select', options: [...] },
  ],
}
```

### 添加新物料

**步骤 1**: 在 `editor/materials/` 对应分类文件中添加定义

```typescript
// materials/basic.tsx 中追加
{
  componentName: 'NutTag',
  title: '标签',
  icon: 'TagOutlined',
  category: 'basic',
  defaultProps: {
    text: '标签',
    type: 'primary',
    round: false,
  },
  configureSchema: [
    { key: 'text', label: '标签文字', type: 'input', defaultValue: '标签' },
    {
      key: 'type', label: '类型', type: 'select', defaultValue: 'primary',
      options: [
        { label: '主要', value: 'primary' },
        { label: '成功', value: 'success' },
        { label: '警告', value: 'warning' },
        { label: '危险', value: 'danger' },
      ],
    },
    { key: 'round', label: '圆角', type: 'switch', defaultValue: false },
  ],
}
```

**步骤 2**: 在 `SchemaRenderer.tsx` 中添加渲染逻辑

```typescript
// SchemaRenderer.tsx 的 renderComponent switch 中追加
case 'NutTag':
  return (
    <div style={{ padding: '4px 12px' }}>
      <span style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: node.props.round ? 99 : 4,
        fontSize: 12,
        // ... 根据 type 设置颜色
      }}>
        {node.props.text}
      </span>
    </div>
  );
```

**步骤 3**: 在小程序渲染器中添加对应分支 (如需要小程序端支持)

`apps/patient-miniapp/src/components/LowCodeRenderer/index.tsx` 中添加相同的 `case` 分支，使用 Taro 组件 (`View`, `Text` 等) 实现。

## 渲染管线

从 Schema JSON 到最终 UI 呈现的完整流程:

```
                  后端 API                   Admin 编辑器                  小程序端
                 +--------+                 +-----------+               +-----------+
  JSON Schema -> | 存储   | -> 加载 Schema   | 编辑态    |  -> 保存     | 运行态    |
  (JSONB)        | (DB)   |   (API)          | 渲染器    |    (API)     | 渲染器    |
                 +--------+                 +-----------+               +-----------+
                                              |                           |
                                        SchemaRenderer              LowCodeRenderer
                                        (React DOM)                 (Taro Components)
                                        + 选中态高亮                 + 原生渲染
                                        + 拖拽交互
                                        + 属性面板
```

### 编辑态渲染 (SchemaRenderer)

位置: `editor/components/SchemaRenderer.tsx`

- 使用 `useEditorStore` 获取当前 Schema
- 每个节点包裹在 `DraggableNode` (可拖拽) 和 `DroppableZone` (可放置) 中
- 选中节点显示蓝色边框和组件名标签
- 画布尺寸固定 375x667 (模拟手机屏幕)

### 运行态渲染 (Admin 预览)

位置: `lowcode/preview.tsx` 中的 `PreviewNodeRenderer`

- 纯展示渲染，无编辑交互
- 支持设备尺寸切换: 手机 (375x667)、平板 (768x1024)、桌面 (1200x800)
- 使用原生 HTML 元素 (`div`, `img` 等)

### 运行态渲染 (小程序)

位置: `apps/patient-miniapp/src/components/LowCodeRenderer/index.tsx`

- 使用 Taro 组件 (`View`, `Text`, `Image`, `Swiper` 等)
- 递归渲染组件树，未知组件 fallback 到 `View` 容器
- 入口页面: `apps/patient-miniapp/src/pages/lowcode/index.tsx`

## 状态管理

编辑器使用 Zustand 管理状态 (`editor/store.ts`):

### Store 状态

| 字段 | 类型 | 说明 |
|------|------|------|
| schema | LowCodeSchema | 当前页面 Schema |
| selectedNodeId | string \| null | 当前选中的节点 ID |
| history | HistoryEntry[] | 历史记录栈 (最多 50 步) |
| historyIndex | number | 当前历史位置索引 |
| loading | boolean | 加载状态 |
| pageId | string \| null | 当前页面 ID (新建时为 null) |
| savedSchema | LowCodeSchema | 上次保存时的 Schema 快照 |

### Store Actions

| Action | 说明 |
|--------|------|
| setSchema(schema) | 设置 Schema 并推入历史记录 |
| selectNode(nodeId) | 选中/取消选中节点 |
| addNode(node, parentId, index) | 向指定父节点的指定位置添加子节点 |
| moveNode(nodeId, newParentId, index) | 移动节点到新的父节点和位置 |
| updateNodeProps(nodeId, props) | 更新节点属性 (合并) |
| removeNode(nodeId) | 删除节点 |
| undo() / redo() | 撤销 / 重做 |
| markSaved() | 标记当前 Schema 为已保存 (用于脏检查) |
| reset() | 重置所有状态到初始值 |

### 拖拽交互

编辑器使用 `@dnd-kit/react` 实现拖拽:

1. **物料面板 -> 画布**: 拖拽 `new-component` 类型数据，创建新节点并插入到目标容器
2. **画布内重排序**: 拖拽 `existing-node` 类型数据，移动已有节点到新位置
3. **安全检查**: 自动防止将节点拖拽到自身内部 (检测子孙关系)

## 页面管理列表

位置: `lowcode/list.tsx`

- 使用 ProTable 组件，支持分页、状态筛选、关键词搜索
- 列: 页面名称、标识 (slug)、描述、状态、创建时间、更新时间
- 操作: 编辑、预览、发布 (仅草稿)、删除 (仅草稿，带确认弹窗)

## 页面预览

位置: `lowcode/preview.tsx`

- 支持三种设备尺寸切换: 手机 / 平板 / 桌面
- 使用独立的 `PreviewNodeRenderer`，不依赖编辑器 Store
- 每次进入自动加载页面 Schema 数据

## 测试

```bash
cd apps/admin
pnpm vitest run src/pages/lowcode/editor/__tests__/store.test.ts
```
