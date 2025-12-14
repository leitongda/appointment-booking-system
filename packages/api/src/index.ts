// 导出请求配置函数
export { setBaseURL, setRequestInterceptor, setResponseInterceptor } from './request';

// 导出 API 模块
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
export {
  consultationFeeTypeApi,
  consultationFeeTemplateApi,
  doctorConsultationFeeApi,
} from './modules/consultation-fee';
export { doctorBookingSettingApi } from './modules/doctor-booking-setting';
export { scheduleTemplateApi } from './modules/schedule-template';
export { customScheduleApi } from './modules/custom-schedule';
export { restDayApi } from './modules/rest-day';
export { scheduleSuspensionApi } from './modules/schedule-suspension';
export { blacklistApi } from './modules/blacklist';

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
export type {
  PatientListItem,
  PatientDetail,
  PatientStatistics,
  PatientUpdateData,
  PatientAppointment,
  PatientAppointmentParams,
  ConsumptionRecord,
  ConsumptionRecordParams,
  PointLog,
  PointLogResult,
  PointAdjustData,
  PointAdjustResult,
  PointSummary,
  PatientListParams,
} from './modules/patient';

// Settings types
export type {
  BookingSettings,
  HospitalInfo,
  WechatConfig,
  SmsConfig,
  BookingRules,
  BookingFieldConfig,
  PatientCardConfig,
} from './modules/settings';

// Blacklist types
export type {
  BlacklistItem,
  BlacklistListParams,
  BlacklistCreateData,
  BlacklistCheckResult,
} from './modules/blacklist';

// Admin Operation Log type
export type { OperationLog } from './modules/admin';

// Consultation Fee types
export type {
  ConsultationFeeTypeCreateData,
  ConsultationFeeTypeUpdateData,
  ConsultationFeeTemplateCreateData,
  DoctorFeeQueryParams,
} from './modules/consultation-fee';

// Doctor Booking Setting types
export type { DoctorBookingSettingListParams } from './modules/doctor-booking-setting';

// Schedule Template types
export type {
  ScheduleTemplateListParams,
  ScheduleTemplateCreateData,
  ScheduleTemplateUpdateData,
  ScheduleGenerateData,
  ScheduleBatchAddData,
} from './modules/schedule-template';

// Custom Schedule types
export type {
  CustomSchedule,
  CustomScheduleListParams,
  CustomScheduleCreateData,
  TimePeriod,
  EffectiveScheduleParams,
} from './modules/custom-schedule';

// Rest Day types
export type {
  RestDay,
  RestDayListParams,
  RestDayCreateData,
} from './modules/rest-day';

// Schedule Suspension types
export type {
  ScheduleSuspension,
  ScheduleSuspensionListParams,
  ScheduleSuspensionCreateData,
  AvailableScheduleForSuspension,
} from './modules/schedule-suspension';

// Schedule Statistics types
export type {
  ScheduleStatisticsItem,
  ScheduleStatisticsResponse,
  ScheduleStatisticsParams,
} from './modules/schedule';
