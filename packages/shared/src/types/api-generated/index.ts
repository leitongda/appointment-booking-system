/**
 * API 自动生成类型入口
 *
 * 本目录由 `pnpm gen:api-types` 自动生成，是后端 OpenAPI schema 的 TypeScript 镜像。
 * 后端是类型的唯一真相源——schema 变更后重新生成即可同步。
 *
 * ┌─────────────────────────────────────────────────────────────┐
 * │  生成命令（项目根目录运行）：                                    │
 * │    pnpm gen:openapi      # 仅导出后端 openapi.json             │
 * │    pnpm gen:api-types    # 导出 + 生成 TS 类型（完整流程）       │
 * └─────────────────────────────────────────────────────────────┘
 *
 * 迁移策略：并存渐进迁移。
 * - 生成的类型放在本目录（api-generated/），不覆盖 packages/shared/src/types/ 下的手写类型。
 * - 新代码优先使用本目录的生成类型；手写类型逐步迁移为 re-export 生成类型。
 * - 这消除了「前后端类型漂移」根因（历史曾因此导致 patient-h5 状态码错位 bug）。
 *
 * 常用导入示例：
 *   import { components } from '@hospital/shared/types/api-generated';
 *   type AppointmentSchema = components['schemas']['AppointmentResponse'];
 *
 *   import { operations } from '@hospital/shared/types/api-generated';
 *   type CreateAppointmentReq = operations['create_appointment_api_v1_appointments_post']['requestBody'];
 */

// 重导出生成文件的所有顶层类型
import type { components } from './schema';

export { paths, webhooks, components, operations } from './schema';

/**
 * 业务实体类型的便捷别名。
 * components['schemas']['XxxResponse'] 这种索引写法较冗长，这里抽成具名类型。
 * 按需补充：新增实体时在下方添加一行别名即可。
 */
// 示例（取消注释并确认 schema 名后使用）：
// export type AppointmentEntity = components['schemas']['AppointmentResponse'];
// export type PatientEntity = components['schemas']['PatientResponse'];

export type SchemaName = keyof components['schemas'];

/**
 * 根据 schema 名取类型。用法：type X = SchemaOf<'AppointmentResponse'>;
 */
export type SchemaOf<N extends SchemaName> = components['schemas'][N];
