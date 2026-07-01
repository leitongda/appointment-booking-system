export * from './common';
export * from './user';
export * from './doctor';
export * from './department';
export * from './schedule';
export * from './appointment';
export * from './store';
export * from './message';
export * from './leave-request';
export * from './feedback';
export * from './consultation-fee';
export * from './doctor-booking-setting';
export * from './region';
export * from './store-visit-type-config';
export * from './rule-set';
export * from './approval';
export * from './lowcode';
export * from './workflow';

// 注意：以上为手写类型（逐步退役中）。
// 后端 OpenAPI 自动生成的类型在 ./api-generated/，是类型的唯一真相源。
// 为避免命名冲突，生成类型不在此处 re-export，请显式导入：
//   import { components, SchemaOf } from '@hospital/shared/src/types/api-generated';
//   type ApptRes = SchemaOf<'AppointmentResponse'>;
// 新代码优先使用生成类型；手写类型迁移为 re-export 生成类型后再从上方移除。
