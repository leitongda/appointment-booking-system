export { authApi } from './modules/auth';
export { userApi } from './modules/user';
export { departmentApi } from './modules/department';
export { doctorApi } from './modules/doctor';
export { scheduleApi } from './modules/schedule';
export { appointmentApi } from './modules/appointment';
export { medicalRecordApi } from './modules/medical-record';
export { contentApi } from './modules/content';
export { statisticsApi } from './modules/statistics';
export { adminApi } from './modules/admin';
export { settingsApi } from './modules/settings';
export { patientApi } from './modules/patient';
export { exportApi } from './modules/export';
export { storeApi } from './modules/store';
export { messageApi } from './modules/message';
export { leaveRequestApi } from './modules/leave-request';
export { feedbackApi } from './modules/feedback';

// Auth types are re-exported from @hospital/shared
export type { LoginParams, LoginResult } from '@hospital/shared';
export type { PatientCreateData } from './modules/user';
export type { DepartmentListParams, DepartmentCreateData } from './modules/department';
export type { DoctorListParams, DoctorCreateData } from './modules/doctor';
export type { ScheduleListParams, ScheduleCreateData, ScheduleBatchCreateData, AvailableSchedule } from './modules/schedule';
export type { AppointmentListParams, AppointmentCreateData, AppointmentStatistics } from './modules/appointment';
export type {
  MedicalRecord,
  MedicalRecordListItem,
  MedicalRecordListParams,
  MedicalRecordCreateData,
  MedicalRecordUpdateData,
} from './modules/medical-record';
export type {
  OverviewData,
  TrendItem,
  RevenueTrendItem,
  StatusStatItem,
  DepartmentRankingItem,
  DoctorRankingItem,
  TimeSlotItem,
  WeekdayItem,
} from './modules/statistics';

// Admin types
export type { Admin, Role, AdminLoginParams, AdminLoginResult } from './modules/admin';

// Content types
export type { Banner, News, Notice } from './modules/content';

// Patient types
export type { PatientListItem, PatientDetail } from './modules/patient';

// Settings types
export type { BookingSettings, HospitalInfo, WechatConfig, SmsConfig, BookingRules } from './modules/settings';

// Admin Operation Log type
export type { OperationLog } from './modules/admin';
