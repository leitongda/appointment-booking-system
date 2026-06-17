# 地图组件抽象与 UX 增强计划

## Context

当前地图选点功能已实现，但存在三个问题：
1. **重复代码** — tenant/form.tsx 和 system/settings.tsx 的 `handleMapLocationOk` 逻辑完全相同（拼接省市区+地址）
2. **样板代码多** — 每个使用场景都要手动维护 `mapModalVisible` 状态、import Modal、写回调函数
3. **UX 可提升** — 缺少定位按钮、搜索无结果提示、搜索高亮等功能

目标：封装为 `FormLocationPicker` 表单字段组件，消除重复代码；同时增强搜索和交互体验。

---

## 组件架构（四层）

```
Layer 0: LocationInfo 类型 + 工具函数     (新建 types.ts)
Layer 1: MapLocationPicker                (核心地图，不变)
Layer 2: MapLocationPickerModal           (Modal 包装，不变)
Layer 3: FormLocationPicker               (新增：ProForm 表单字段组件)
```

---

## P0 — 消除重复代码

### P0-1: 提取 LocationInfo 类型和工具函数

**新建** `apps/admin/src/components/MapLocationPicker/types.ts`

- 从 `index.tsx` 搬出 `LocationInfo` 接口
- 新增工具函数：
  - `formatFullAddress(location)` — 拼接省市区+地址（消除 tenant/settings 重复）
  - `locationToFields(location)` — 转为 6 字段对象（store 的逻辑）
- 在 `index.tsx` 中 re-export，保持 `@/components/MapLocationPicker` 导入路径兼容

### P0-2: 新建 FormLocationPicker 组件

**新建** `apps/admin/src/components/formFields/FormLocationPicker.tsx`
**修改** `apps/admin/src/components/formFields/index.ts`（增加导出）

Props 设计：
```typescript
interface FormLocationPickerProps {
  name: string;                    // 表单字段名
  label?: string;
  mode?: 'structured' | 'concatenated';  // 输出模式
  fieldNames?: { province?, city?, district?, address?, longitude?, latitude? };  // structured 模式子字段名
  buttonText?: string;             // 按钮文本，默认 "地图选点"
  disabled?: boolean;
  modalTitle?: string;
  getInitialValue?: (formValues: any) => LocationInfo | undefined;  // 编辑时构造初始值
  onLocationChange?: (location: LocationInfo) => void;  // 额外回调
}
```

内部逻辑：
- `Form.Item` 包装，内部维护 `mapModalVisible` 状态
- 渲染只读 Input（显示地址）+ Button（触发 Modal）
- `mode="structured"` — 选点后 `form.setFieldsValue` 填充所有子字段
- `mode="concatenated"` — 选点后拼接字符串写入 `name` 字段
- 使用 `Form.useFormInstance()` 获取 form 实例

### P0-3: 重构 tenant/form.tsx

删除：`mapModalVisible` 状态、`handleMapLocationOk`、MapLocationPickerModal import 和实例

替换为：
```tsx
<FormLocationPicker name="address" label="详细地址" mode="concatenated" />
```

### P0-4: 重构 system/settings.tsx

删除：`hospitalMapModalVisible` 状态、`handleHospitalMapLocationOk`、MapLocationPickerModal import 和实例

替换为：
```tsx
<FormLocationPicker name="address" label="医院地址" mode="concatenated" disabled={!canEditSettings} />
```

### P0-5: 重构 store/form.tsx

删除：`mapModalVisible` 状态、`handleMapLocationOk`、MapLocationPickerModal import 和实例

替换为：
```tsx
<FormLocationPicker
  name="address"
  label="详细地址"
  mode="structured"
  fieldNames={{ province: 'province', city: 'city', district: 'district', address: 'address', longitude: 'longitude', latitude: 'latitude' }}
  getInitialValue={(vals) => vals?.longitude && vals?.latitude ? { ... } : undefined}
/>
```

保留 province/city/district 的 ProFormText 字段（有独立验证规则），FormLocationPicker 通过 `setFieldsValue` 自动填充。

---

## P1 — UX 提升

### P1-1: 定位按钮

**修改** `MapLocationPicker/index.tsx`

- 搜索框旁添加"定位"按钮（`AimOutlined`）
- 调用 `navigator.geolocation.getCurrentPosition` 获取当前位置
- 逆地理编码后移动标记到当前位置
- 处理权限拒绝/超时，显示 message 提示

### P1-2: 搜索无结果提示

**修改** `MapLocationPicker/index.tsx`

- `searchPoi` 返回空数组时，options 中添加"未找到相关地点"提示项
- AutoComplete 添加 `notFoundContent`

### P1-3: 搜索结果高亮

**修改** `MapLocationPicker/index.tsx`

- `searchPoi` 的 label 渲染中，对匹配关键词部分用 `<mark>` 高亮

### P1-4: 地址展示优化

**修改** `MapLocationPicker/index.tsx`

- 省市区用 Tag 标签展示
- 经纬度可点击复制（`Typography.Paragraph` 的 `copyable`）
- 增加"清除位置"按钮

### P1-5: MapLocationPickerModal Props 对齐

**修改** `MapLocationPickerModal/index.tsx`

- `visible` 改为 `open`（antd 5+ 推荐），保留 `visible` 兼容
- 透传 `mapHeight`、`placeholder` 到内部 MapLocationPicker

---

## P2 — 可选

| 功能 | 改动文件 | 说明 |
|------|---------|------|
| 搜索历史 | MapLocationPicker | localStorage 存最近 10 条，聚焦时显示 |
| 缩放控件 | MapLocationPicker + typings.d.ts | 添加 ToolBar、Scale 控件 |
| 经纬度验证 | formValidators.ts | 中国境内范围校验 |
| 移动端适配 | MapLocationPicker + Modal | 响应式布局，移动端全屏 Modal |

---

## 验证方式

1. **TypeScript 检查** — `npx tsc --noEmit` 无新增错误
2. **功能验证** — 启动 `pnpm dev:admin`，分别测试：
   - 门店表单：编辑模式下打开地图应回显已有位置，选点后省市区自动填充
   - 租户表单：选点后地址字段自动拼接省市区
   - 系统设置-医院信息：选点后地址字段自动拼接，disabled 状态下按钮不可点
3. **回归验证** — 确认 MapLocationPickerModal 仍可独立使用（未被废弃）

---

## 关键文件

| 文件 | 操作 |
|------|------|
| `components/MapLocationPicker/types.ts` | 新建 |
| `components/MapLocationPicker/index.tsx` | 修改（re-export + P1 UX 增强） |
| `components/formFields/FormLocationPicker.tsx` | 新建 |
| `components/formFields/index.ts` | 修改（增加导出） |
| `components/MapLocationPickerModal/index.tsx` | 修改（P1-5 Props 对齐） |
| `pages/store/form.tsx` | 重构 |
| `pages/tenant/form.tsx` | 重构 |
| `pages/system/settings.tsx` | 重构 |
