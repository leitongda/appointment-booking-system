/**
 * Settings 子模块入口。
 *
 * 从 settings.tsx（1474 行）全量重构抽取，每个 tab 为独立组件。
 * settings.tsx 现在是薄编排层（~200 行），负责状态管理 + 权限 + tab 路由。
 */
export { default as BookingTab } from './BookingTab';
export { default as HospitalTab } from './HospitalTab';
export { default as BookingFieldsTab } from './BookingFieldsTab';
export { default as PatientCardTab } from './PatientCardTab';
export { default as BlacklistTab } from './BlacklistTab';
export { default as EmailTab } from './EmailTab';
export { default as WechatTab } from './WechatTab';
export { default as ImageTab } from './ImageTab';
export { default as SmsTab } from './SmsTab';
export { default as SecurityTab } from './SecurityTab';
export { default as SourceReleaseTab } from './SourceReleaseTab';

export * from './types';
export * from './defaults';
