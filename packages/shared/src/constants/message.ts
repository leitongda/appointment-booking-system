/**
 * 消息中心 Tab 配置常量
 */

// 患者端消息分类 (H5 + 小程序统一)
export const PATIENT_MESSAGE_TABS = [
  { key: 'all', label: '全部' },
  { key: 'appointment', label: '预约' },
  { key: 'consultation', label: '就诊' },
  { key: 'stop_clinic', label: '停诊' },
  { key: 'feedback', label: '反馈' },
  { key: 'system', label: '系统' },
] as const;

// 医生端消息分类
export const DOCTOR_MESSAGE_TABS = [
  { key: 'all', label: '全部' },
  { key: 'schedule', label: '排班' },
  { key: 'appointment', label: '预约' },
  { key: 'stop_clinic', label: '停诊' },
  { key: 'feedback', label: '反馈' },
  { key: 'system', label: '系统' },
] as const;

// Tab key 类型定义
export type PatientMessageTabKey = typeof PATIENT_MESSAGE_TABS[number]['key'];
export type DoctorMessageTabKey = typeof DOCTOR_MESSAGE_TABS[number]['key'];
