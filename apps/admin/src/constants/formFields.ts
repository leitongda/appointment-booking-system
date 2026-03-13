/**
 * 表单字段选项常量
 *
 * 集中管理各表单中重复使用的选项常量
 */

/**
 * 公告类型选项
 */
export const NOTICE_TYPE_OPTIONS = [
  { label: '系统公告', value: 1 },
  { label: '停诊通知', value: 2 },
  { label: '活动通知', value: 3 },
] as const;

/**
 * 新闻类型选项
 */
export const NEWS_TYPE_OPTIONS = [
  { label: '医院动态', value: 1 },
  { label: '健康知识', value: 2 },
  { label: '政策法规', value: 3 },
] as const;

/**
 * 轮播图链接类型选项
 */
export const BANNER_LINK_TYPE_OPTIONS = [
  { label: '无链接', value: 0 },
  { label: '内部链接', value: 1 },
  { label: '外部链接', value: 2 },
] as const;

/**
 * 轮播图展示位置选项
 */
export const BANNER_POSITION_OPTIONS = [
  { label: '首页', value: 'home' },
  { label: '我的', value: 'mine' },
] as const;

/**
 * 预约类型选项
 * 注意: 此常量已在 @hospital/shared 中定义,这里为了方便使用而重新导出
 * 如果需要修改,请更新 packages/shared/src/constants/schedule.ts
 */
export const APPOINTMENT_TYPE_OPTIONS = [
  { label: '加急', value: 'urgent' },
  { label: '普通', value: 'normal' },
  { label: '专家', value: 'expert' },
  { label: '医保', value: 'medical_insurance' },
  { label: '自费', value: 'self_pay' },
] as const;

/**
 * 排班方式选项
 * 注意: 此常量已在 @hospital/shared 中定义,这里为了方便使用而重新导出
 * 如果需要修改,请更新 packages/shared/src/constants/schedule.ts
 */
export const SCHEDULE_MODE_OPTIONS = [
  { label: '每周循环', value: 'weekly' },
  { label: '每月第一周', value: 'month_week_1' },
  { label: '每月第二周', value: 'month_week_2' },
  { label: '每月第三周', value: 'month_week_3' },
  { label: '每月第四周', value: 'month_week_4' },
  { label: '每月第五周', value: 'month_week_5' },
  { label: '本年奇数周', value: 'year_odd_week' },
  { label: '本年偶数周', value: 'year_even_week' },
] as const;

/**
 * 邮件模板类型选项
 * 注意: 此常量已在 @hospital/api 中定义,这里为了方便使用而重新导出
 * 如果需要修改,请更新 packages/api/src/modules/email-template.ts
 */
export const EMAIL_TEMPLATE_TYPE_OPTIONS = [
  { label: '预约确认', value: 'appointment_confirm' },
  { label: '就诊提醒', value: 'appointment_remind' },
  { label: '预约取消', value: 'appointment_cancel' },
  { label: '停诊通知（旧）', value: 'stop_clinic' },
  { label: '自定义', value: 'custom' },
  { label: '新预约通知', value: 'appointment_created' },
  { label: '预约取消通知', value: 'appointment_cancelled' },
  { label: '签到通知', value: 'checkin' },
  { label: '叫号通知', value: 'call_patient' },
  { label: '就诊完成通知', value: 'visit_completed' },
  { label: '爽约通知', value: 'no_show' },
  { label: '停诊通知', value: 'schedule_suspended' },
] as const;
