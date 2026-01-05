/**
 * 统一分页配置
 *
 * 用于消除代码中的硬编码分页值，提高代码可维护性
 */

/**
 * 分页配置常量
 */
export const PAGINATION_CONFIG = {
  /**
   * 列表默认分页大小
   * 用于 ProTable、Ant Table 等列表组件
   */
  DEFAULT_PAGE_SIZE: 10,

  /**
   * 列表分页选项
   * 用户可以选择的分页大小
   */
  PAGE_SIZE_OPTIONS: [10, 20, 50, 100],

  /**
   * 筛选器下拉框最大数量
   * 用于科室、门店、医生等选择器
   * 适中大小，既保证完整性又避免加载过多数据
   */
  SELECT_MAX_SIZE: 200,

  /**
   * 日历组件最大数量
   * 用于月视图、周视图等日历组件
   * 假设每天最多10个排班，一个月最多300个
   */
  CALENDAR_MAX_SIZE: 500,

  /**
   * 表格选择器最大数量
   * 用于 Transfer、Select 等需要显示所有选项的组件
   */
  TABLE_SELECT_MAX_SIZE: 1000,
} as const;

/**
 * 根据场景获取合适的分页大小
 *
 * @param scene 使用场景
 * @returns 分页大小
 */
export function getPageSize(scene: 'DEFAULT_PAGE_SIZE' | 'SELECT_MAX_SIZE' | 'CALENDAR_MAX_SIZE' | 'TABLE_SELECT_MAX_SIZE'): number {
  return PAGINATION_CONFIG[scene];
}

/**
 * 默认分页参数
 * 用于 API 请求
 */
export const DEFAULT_PAGINATION_PARAMS = {
  page: 1,
  pageSize: PAGINATION_CONFIG.DEFAULT_PAGE_SIZE,
} as const;
