/**
 * 响应式设计断点配置
 *
 * 与 Ant Design Grid 系统对齐
 * xs: <576px (手机)
 * sm: >=576px (小平板)
 * md: >=768px (平板)
 * lg: >=992px (桌面)
 * xl: >=1200px (大桌面)
 * xxl: >=1600px (超大桌面)
 */

/**
 * 断点尺寸（像素）
 */
export const BREAKPOINTS = {
  xs: 0,
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1600,
} as const;

/**
 * 设备类型
 */
export type DeviceType = 'mobile' | 'tablet' | 'desktop' | 'largeDesktop';

/**
 * 响应式布局配置
 */
export const RESPONSIVE_CONFIG = {
  /** 表格横向滚动阈值 */
  tableScrollThreshold: {
    mobile: 480,
    tablet: 768,
    desktop: 1200,
  },
  /** 侧边栏宽度 */
  sidebarWidth: {
    collapsed: 80,
    expanded: 200,
  },
  /** 表单标签宽度 */
  formLabelWidth: {
    mobile: '100%',
    tablet: 120,
    desktop: 150,
  },
  /** 弹窗宽度 */
  modalWidth: {
    small: {
      mobile: '95%',
      tablet: 420,
      desktop: 520,
    },
    medium: {
      mobile: '95%',
      tablet: 600,
      desktop: 720,
    },
    large: {
      mobile: '95%',
      tablet: 800,
      desktop: 1000,
    },
  },
  /** 卡片间距 */
  cardGutter: {
    mobile: 8,
    tablet: 12,
    desktop: 16,
  },
  /** 表单项间距 */
  formItemGutter: {
    mobile: 8,
    tablet: 12,
    desktop: 16,
  },
} as const;

/**
 * 表格列宽配置
 */
export const TABLE_COLUMN_WIDTH = {
  /** 操作列 */
  operations: {
    mobile: 80,
    tablet: 120,
    desktop: 150,
  },
  /** 状态列 */
  status: 80,
  /** 时间列 */
  datetime: 160,
  /** 短文本列 */
  shortText: 100,
  /** 中等文本列 */
  mediumText: 150,
  /** 长文本列 */
  longText: 200,
} as const;

/**
 * ProTable 响应式配置
 */
export const PROTABLE_RESPONSIVE = {
  /** 默认滚动宽度 */
  defaultScrollX: 1200,
  /** 密度配置 */
  density: {
    mobile: 'small' as const,
    tablet: 'middle' as const,
    desktop: 'default' as const,
  },
  /** 分页配置 */
  pagination: {
    mobile: {
      pageSize: 10,
      simple: true,
    },
    tablet: {
      pageSize: 20,
      simple: false,
    },
    desktop: {
      pageSize: 20,
      simple: false,
    },
  },
} as const;

/**
 * 表单布局配置
 */
export const FORM_LAYOUT = {
  /** 表单布局 */
  layout: {
    mobile: 'vertical' as const,
    tablet: 'horizontal' as const,
    desktop: 'horizontal' as const,
  },
  /** 栅格列配置 */
  colSpan: {
    mobile: 24,
    tablet: 12,
    desktop: 8,
  },
  /** 输入框宽度 */
  inputWidth: {
    mobile: '100%',
    tablet: 'md',
    desktop: 'md',
  },
} as const;

/**
 * 表格响应式配置
 */
export const TABLE_CONFIG = {
  /** 分页每页条数 */
  pageSize: {
    mobile: 10,
    tablet: 20,
    desktop: 20,
  },
  /** 简易分页 */
  simplePagination: {
    mobile: true,
    tablet: false,
    desktop: false,
  },
  /** 密度 */
  density: {
    mobile: 'small' as const,
    tablet: 'middle' as const,
    desktop: 'default' as const,
  },
  /** 操作列宽度 */
  operationsWidth: {
    mobile: 80,
    tablet: 120,
    desktop: 150,
  },
} as const;

/**
 * 弹窗响应式配置
 */
export const MODAL_CONFIG = {
  /** 小弹窗 */
  small: {
    mobile: '95%',
    tablet: 420,
    desktop: 520,
  },
  /** 中弹窗 */
  medium: {
    mobile: '95%',
    tablet: 600,
    desktop: 720,
  },
  /** 大弹窗 */
  large: {
    mobile: '95%',
    tablet: 800,
    desktop: 1000,
  },
} as const;

export type Breakpoint = keyof typeof BREAKPOINTS;
export type ResponsiveConfig = typeof RESPONSIVE_CONFIG;
