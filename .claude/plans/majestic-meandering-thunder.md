# 修复：保存失败后表单数据被重置

## Context

管理员编辑页面在保存失败后，用户修改过的表单字段会被重置为服务端原始数据。此问题影响所有 13 个使用 FormPage 的表单页面。

根因链路（多层叠加）：
1. `useFormSubmit:187` 的 `throw error` 将错误 re-throw 给 ProForm，ProForm 可能触发 error boundary 导致组件 remount
2. `useFormInitialValues` 的 `useMemo` 依赖 `[data, switchFields, defaults, transform]`，调用方传入的内联对象/函数每次渲染都是新引用，导致 `initialValues` 持续重算
3. 提交失败后 `setSubmitting(false)` 触发重渲染 → 新 `initialValues` 引用 → `FormPage` 的 `useEffect` 调用 `setFieldsValue` 覆盖用户编辑

## ahooks 引入

ahooks 目前仅作为 antd-mobile 的传递依赖存在，项目无直接引用。安装为直接依赖，使用 `useMount` 替代 `useRef + useEffect` 的首次初始化守卫模式。

```bash
cd apps/admin && pnpm add ahooks
```

## 修改方案（3 处文件）

### 1. useFormSubmit — 移除 throw error（根因修复）

文件：`apps/admin/src/hooks/useFormSubmit.ts`

**Line 187**: 移除 `throw error`。错误已通过 `message.error()` 展示给用户，re-throw 会导致 ProForm 内部 reject 链路触发 error boundary，组件 remount 后 `initializedRef` 丢失。

```tsx
} catch (error: any) {
  message.error(error.message || errorMessage);
  // 不再 re-throw，避免 ProForm 触发 error boundary remount
} finally {
  setSubmitting(false);
}
```

### 2. FormPage — useMount 初始化 + 移除 ProForm initialValues（核心防护）

文件：`apps/admin/src/components/FormPage/index.tsx`

用 `useMount` 替代 `useRef + useEffect` 的首次初始化模式。`useMount` 仅在组件挂载时执行一次，天然避免重渲染时重复设置表单值。

```tsx
import { useMount } from 'ahooks';

// 仅挂载时设置一次表单值
useMount(() => {
  if (initialValues && formRef.current) {
    formRef.current.setFieldsValue(initialValues);
  }
});
```

同时移除 `<ProForm initialValues={initialValues}>`，避免 ProForm 用它做内部 reset。

回退上一轮的 `initializedRef + useEffect` 改动。

### 3. useFormInitialValues — 稳定所有内联依赖（防御性修复）

文件：`apps/admin/src/hooks/useFormInitialValues.ts`

用 `useRef` 持有 `transform`、`switchFields`、`defaults` 三个可能内联的引用，从 `useMemo` 依赖数组中移除。仅 `[data]` 作为真正的依赖。

```tsx
const transformRef = useRef(transform);
transformRef.current = transform;
const switchFieldsRef = useRef(switchFields);
switchFieldsRef.current = switchFields;
const defaultsRef = useRef(defaults);
defaultsRef.current = defaults;

const initialValues = useMemo<Partial<T>>(() => {
  // 使用 ref.current 读取最新值
}, [data]);  // 仅 data 变化时重算
```

（transform 的 useRef 已在上一轮完成，需补充 switchFields 和 defaults）

## 涉及文件

| 文件 | 修改内容 | 状态 |
|---|---|---|
| `apps/admin/package.json` | 安装 ahooks 直接依赖 | 待执行 |
| `apps/admin/src/hooks/useFormSubmit.ts` | 移除 `throw error`（line 187） | 待修改 |
| `apps/admin/src/components/FormPage/index.tsx` | useMount 替代 useRef+useEffect，移除 ProForm initialValues | 需回退重做 |
| `apps/admin/src/hooks/useFormInitialValues.ts` | useRef 稳定 transform/switchFields/defaults | 部分完成（需补充 switchFields/defaults） |

## 受影响页面（共 13 个）

全部使用 FormPage 的页面都会受益，无需逐个修改：
- 9 个使用 useFormSubmit 的页面：role-form、shift-type-form、consultation-fee-type-form、user-form、email-template-form、department/form、banner-form、news-form、notice-form
- 4 个手动处理提交的页面：doctor/form、store/form、custom-form、rest-day-form

## 验证方式

1. 打开管理员编辑页面，修改邮箱为已被占用的值，点击保存
2. 确认错误提示正常显示，表单字段保留用户修改的值（不被重置）
3. 修改为合法值保存成功，确认正常跳转
4. 新增管理员页面测试，确认初始值正确加载
5. 测试其他表单页面（如角色编辑、科室编辑）确认无回归
