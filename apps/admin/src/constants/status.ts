/**
 * 状态相关常量
 */

/**
 * 状态枚举
 */
export enum Status {
  Disabled = 0,
  Enabled = 1,
}

/**
 * 状态选项(用于表单)
 */
export const STATUS_OPTIONS = [
  { label: '启用', value: Status.Enabled },
  { label: '禁用', value: Status.Disabled },
] as const;

/**
 * 状态显示映射(用于列表)
 */
export const STATUS_MAP = {
  [Status.Enabled]: { text: '启用', status: 'Success' },
  [Status.Disabled]: { text: '禁用', status: 'Default' },
} as const;
