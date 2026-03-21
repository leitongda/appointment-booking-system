/**
 * 统一常量配置
 *
 * 集中管理应用中使用的各种常量，避免在各个组件中重复定义
 */

export { PAGINATION_CONFIG, getPageSize, DEFAULT_PAGINATION_PARAMS } from './pagination';

export {
  PATTERNS,
  MESSAGES,
  getCodePattern,
  getCodeMessage,
  type CodeFormatType,
} from './validation';

export { Status, STATUS_OPTIONS, STATUS_MAP } from './status';

export {
  NOTICE_TYPE_OPTIONS,
  NEWS_TYPE_OPTIONS,
  BANNER_LINK_TYPE_OPTIONS,
  BANNER_POSITION_OPTIONS,
  APPOINTMENT_TYPE_OPTIONS,
  SCHEDULE_MODE_OPTIONS,
  EMAIL_TEMPLATE_TYPE_OPTIONS,
} from './formFields';
import { GENDER_MAP as SHARED_GENDER_MAP } from '@hospital/shared';

export const GENDER_MAP = SHARED_GENDER_MAP;

export const GENDER_OPTIONS = Object.entries(SHARED_GENDER_MAP).map(([value, label]) => ({
  label,
  value: Number(value),
}));

/**
 * 学历选项
 */
export const EDUCATION_OPTIONS = [
  { label: '专科', value: '专科' },
  { label: '本科', value: '本科' },
  { label: '硕士', value: '硕士' },
  { label: '博士', value: '博士' },
  { label: '博士后', value: '博士后' },
] as const;

/**
 * 时段选项
 */
export const TIME_SLOT_OPTIONS = [
  { label: '上午', value: 'morning' },
  { label: '下午', value: 'afternoon' },
  { label: '晚上', value: 'evening' },
] as const;

/**
 * 星期选项
 */
export const WEEKDAY_OPTIONS = [
  { label: '星期一', value: 1 },
  { label: '星期二', value: 2 },
  { label: '星期三', value: 3 },
  { label: '星期四', value: 4 },
  { label: '星期五', value: 5 },
  { label: '星期六', value: 6 },
  { label: '星期日', value: 7 },
] as const;

/**
 * 预约状态选项
 */
export const APPOINTMENT_STATUS_OPTIONS = [
  { label: '待就诊', value: 'pending' },
  { label: '已签到', value: 'checked_in' },
  { label: '已完成', value: 'completed' },
  { label: '已取消', value: 'cancelled' },
  { label: '已停诊', value: 'suspended' },
] as const;

/**
 * 排班状态选项
 */
export const SCHEDULE_STATUS_OPTIONS = [
  { label: '正常', value: 'normal' },
  { label: '停诊', value: 'suspended' },
  { label: '满员', value: 'full' },
] as const;

/**
 * 是否选项
 */
export const YES_NO_OPTIONS = [
  { label: '是', value: 1 },
  { label: '否', value: 0 },
] as const;

/**
 * 排序方式选项
 */
export const SORT_ORDER_OPTIONS = [
  { label: '正序', value: 'asc' },
  { label: '倒序', value: 'desc' },
] as const;

/**
 * 常用页面大小选项
 */
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;
