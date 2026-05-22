/**
 * 表单字段选项常量
 *
 * 集中管理各表单中重复使用的选项常量
 *
 * 注意：以下类型已迁移到字典管理，通过 useDict hook 获取：
 * P0: notice_type, news_type, banner_link_type, banner_position,
 *     education, doctor_page_style, id_card_type, patient_relationship,
 *     booking_notice_type, processing_method
 * P1: feedback_type, support_ticket_type, support_ticket_priority,
 *     message_type, email_template_type, notification_event_type,
 *     rule_type, extra_quota_type
 * P2: appointment_type
 */

// APPOINTMENT_TYPE_OPTIONS 已迁移到字典管理 → useDict('appointment_type')

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

// EMAIL_TEMPLATE_TYPE_OPTIONS 已迁移到字典管理 → useDict('email_template_type')
