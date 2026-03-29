/**
 * 常量定义
 */

// 预约状态（与后端API保持一致）
export const APPOINTMENT_STATUS = {
  PENDING: 0,      // 待支付
  CONFIRMED: 1,    // 已预约
  SIGNED_IN: 2,    // 已签到
  WAITING: 3,      // 候诊中
  IN_PROGRESS: 4,  // 就诊中
  COMPLETED: 5,    // 已完成
  CANCELLED: 6,    // 已取消
  EXPIRED: 7,      // 已过期
  NO_SHOW: 8,      // 爽约
} as const;

// 预约状态文本映射
export const APPOINTMENT_STATUS_TEXT = {
  [APPOINTMENT_STATUS.PENDING]: '待支付',
  [APPOINTMENT_STATUS.CONFIRMED]: '已预约',
  [APPOINTMENT_STATUS.SIGNED_IN]: '已签到',
  [APPOINTMENT_STATUS.WAITING]: '候诊中',
  [APPOINTMENT_STATUS.IN_PROGRESS]: '就诊中',
  [APPOINTMENT_STATUS.COMPLETED]: '已完成',
  [APPOINTMENT_STATUS.CANCELLED]: '已取消',
  [APPOINTMENT_STATUS.EXPIRED]: '已过期',
  [APPOINTMENT_STATUS.NO_SHOW]: '爽约',
} as const;

// 预约状态颜色
export const APPOINTMENT_STATUS_COLOR = {
  [APPOINTMENT_STATUS.PENDING]: 'orange',
  [APPOINTMENT_STATUS.CONFIRMED]: '#1890ff',
  [APPOINTMENT_STATUS.SIGNED_IN]: '#52c41a',
  [APPOINTMENT_STATUS.WAITING]: '#722ed1',
  [APPOINTMENT_STATUS.IN_PROGRESS]: '#faad14',
  [APPOINTMENT_STATUS.COMPLETED]: '#52c41a',
  [APPOINTMENT_STATUS.CANCELLED]: '#d9d9d9',
  [APPOINTMENT_STATUS.EXPIRED]: '#d9d9d9',
  [APPOINTMENT_STATUS.NO_SHOW]: '#f5222d',
} as const;

// 性别
export const GENDER = {
  MALE: 1,
  FEMALE: 2
} as const;

// 性别文本映射
export const GENDER_TEXT = {
  [GENDER.MALE]: '男',
  [GENDER.FEMALE]: '女'
} as const;

// 就诊人关系
export const PATIENT_RELATIONSHIP = [
  { value: 'self', label: '本人' },
  { value: 'parent', label: '父母' },
  { value: 'child', label: '子女' },
  { value: 'spouse', label: '配偶' },
  { value: 'other', label: '其他' }
] as const;

// 排班时段
export const TIME_SLOT = {
  MORNING: 'morning',
  AFTERNOON: 'afternoon',
  EVENING: 'evening'
} as const;

// 排班时段文本映射
export const TIME_SLOT_TEXT = {
  [TIME_SLOT.MORNING]: '上午',
  [TIME_SLOT.AFTERNOON]: '下午',
  [TIME_SLOT.EVENING]: '晚上'
} as const;

// 号源状态
export const BOOKING_STATUS = {
  NOT_OPEN: 'not_open',
  AVAILABLE: 'available',
  CLOSING_SOON: 'closing_soon',
  FULL: 'full',
  CLOSED: 'closed'
} as const;

// 号源状态文本映射
export const BOOKING_STATUS_TEXT = {
  [BOOKING_STATUS.NOT_OPEN]: '未开放',
  [BOOKING_STATUS.AVAILABLE]: '可预约',
  [BOOKING_STATUS.CLOSING_SOON]: '即将截止',
  [BOOKING_STATUS.FULL]: '已约满',
  [BOOKING_STATUS.CLOSED]: '已截止'
} as const;

// 号源状态颜色
export const BOOKING_STATUS_COLOR = {
  [BOOKING_STATUS.NOT_OPEN]: '#999999',
  [BOOKING_STATUS.AVAILABLE]: '#52c41a',
  [BOOKING_STATUS.CLOSING_SOON]: '#faad14',
  [BOOKING_STATUS.FULL]: '#f5222d',
  [BOOKING_STATUS.CLOSED]: '#999999'
} as const;

// 紧急程度
export const URGENCY_LEVEL = {
  NORMAL: 'normal',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical'
} as const;

// 紧急程度文本映射
export const URGENCY_LEVEL_TEXT = {
  [URGENCY_LEVEL.NORMAL]: '正常',
  [URGENCY_LEVEL.MEDIUM]: '紧张',
  [URGENCY_LEVEL.HIGH]: '很紧张',
  [URGENCY_LEVEL.CRITICAL]: '非常紧张'
} as const;

// 收藏类型
export const FAVORITE_TYPE = {
  DOCTOR: 'doctor',
  DEPARTMENT: 'department'
} as const;

// 收藏类型文本映射
export const FAVORITE_TYPE_TEXT = {
  [FAVORITE_TYPE.DOCTOR]: '医生',
  [FAVORITE_TYPE.DEPARTMENT]: '科室'
} as const;

// 反馈类型
export const FEEDBACK_TYPE = [
  { value: 'bug', label: '功能异常' },
  { value: 'suggestion', label: '功能建议' },
  { value: 'complaint', label: '投诉' },
  { value: 'other', label: '其他' }
] as const;

// 轮播图链接类型
export const BANNER_LINK_TYPE = {
  NONE: 0,
  INTERNAL: 1,
  EXTERNAL: 2
} as const;

// 存储键名
export const STORAGE_KEYS = {
  TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  USER_INFO: 'user_info',
  STORE_ID: 'store_id',
  STORE_INFO: 'store_info',
  BOOKING_RULES: 'booking_rules',
  HOSPITAL_INFO: 'hospital_info'
} as const;

// 分页配置
export const PAGINATION = {
  DEFAULT_PAGE: 1,
  DEFAULT_PAGE_SIZE: 10,
  MAX_PAGE_SIZE: 100
} as const;

// 图片上传配置
export const IMAGE_UPLOAD = {
  MAX_SIZE: 10 * 1024 * 1024, // 10MB
  MAX_COUNT: 9,
  ACCEPT_TYPES: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
} as const;

// 错误码
export const ERROR_CODE = {
  SUCCESS: 0,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  SERVER_ERROR: 500
} as const;
