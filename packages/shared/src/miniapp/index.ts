// 小程序共享模块
// 统一导出 patient-miniapp 和 miniapp-instance 共用的工具函数、hooks、组件

// 工具函数
export * from './url';
export * from './payment';
export * from './checkin';
export * from './store';
export * from './fontMode';
export * from './navigate';
export * from './wechatAuth';
export * from './theme';

// Stubs（小程序环境 polyfill）
export { default as axiosStub, create as createAxiosStub } from './stubs/empty-axios';
export { default as JSEncryptStub } from './stubs/empty-module';

// Hooks
export * from './hooks';

// Components（Phase 3 填充）
export * from './components';
