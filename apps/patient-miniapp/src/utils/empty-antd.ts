/**
 * 空模块 - 用于在小程序环境中替代 antd/pro-components
 * 
 * 小程序环境不支持这些 PC 端组件库，但由于 @hospital/shared 包
 * 导出了使用这些库的组件 (RegionSelector)，构建时会尝试加载它们。
 * 我们用这个空模块替代，避免构建错误。
 */

// 导出空对象，作为默认导出和命名导出
const Empty = {};

// ProFormCascader 的空实现
export const ProFormCascader = () => null;

// 其他常用的 antd 组件空导出
export const Button = () => null;
export const Input = () => null;
export const Form = () => null;
export const Select = () => null;
export const Cascader = () => null;
export const Modal = () => null;
export const message = {
  success: () => {},
  error: () => {},
  warning: () => {},
  info: () => {},
  loading: () => {},
};
export const notification = {
  success: () => {},
  error: () => {},
  warning: () => {},
  info: () => {},
  open: () => {},
};

// 图标空导出
export const DownOutlined = () => null;
export const UpOutlined = () => null;
export const LoadingOutlined = () => null;

// 默认导出
export default Empty;

