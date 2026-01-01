/**
 * 时间单位
 */
export type TimeUnit = 'hours' | 'days';

/**
 * 复诊范围
 */
export type VisitScope = 'same_doctor' | 'same_department' | 'same_store';

/**
 * 门店复诊规则配置
 */
export interface StoreVisitTypeConfig {
  id?: string;
  storeId: string;
  storeName?: string;
  timeLimit: number;
  timeUnit: TimeUnit;
  scope: VisitScope;
  status: number;
  createdAt?: string;
  updatedAt?: string;
}

/**
 * 创建/更新配置请求
 */
export interface StoreVisitTypeConfigUpdate {
  timeLimit?: number;
  timeUnit?: TimeUnit;
  scope?: VisitScope;
  status?: number;
}

/**
 * 时间单位选项
 */
export const TIME_UNIT_OPTIONS = [
  { value: 'hours', label: '小时' },
  { value: 'days', label: '天' },
];

/**
 * 复诊范围选项
 */
export const VISIT_SCOPE_OPTIONS = [
  { value: 'same_doctor', label: '同一医生' },
  { value: 'same_department', label: '同一科室' },
  { value: 'same_store', label: '同一门店' },
];

