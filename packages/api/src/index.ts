// 导出请求配置函数和错误类
export { 
  setBaseURL, 
  getBaseURL,
  setHttpClient,
  getHttpClient,
  setRequestInterceptor, 
  setResponseInterceptor, 
  ApiError,
  request,
} from './request';
export type { HttpClient } from './request';

// 导出 API 配置
export { API_CONFIG, getApiBaseUrl, setApiConfig, resetApiConfig } from './config';
export type { ApiConfig } from './config';

// 导出请求适配器（用于小程序等非浏览器环境）
export { createTaroAdapter, getTaroToken, setTaroToken } from './adapters';
export type { TaroAdapterConfig } from './adapters';

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
  storeFeeTemplateApi,
  doctorConsultationFeeApi,
} from './modules/consultation-fee';
export { doctorBookingSettingApi } from './modules/doctor-booking-setting';
export { scheduleTemplateApi } from './modules/schedule-template';
export { customScheduleApi } from './modules/custom-schedule';
export { restDayApi } from './modules/rest-day';
export { scheduleSuspensionApi } from './modules/schedule-suspension';
export { blacklistApi } from './modules/blacklist';
export { uploadApi } from './modules/upload';
export { emailTemplateApi, EMAIL_TEMPLATE_TYPE_OPTIONS } from './modules/email-template';
export { dataApi } from './modules/data';
export type { ImportResult } from './modules/data';
export { userManageApi } from './modules/user-manage';
export { favoriteApi } from './modules/favorite';
export { bookingNoticeApi } from './modules/booking-notice';
export { storeVisitTypeConfigApi } from './modules/store-visit-type-config';
export type { 
  UserListItem, 
  UserDetail, 
  UserCard, 
  UserListParams,
  UserUpdateData,
  CardCreateData,
  CardUpdateData,
} from './modules/user-manage';

// Store types
export type { StoreAdmin } from './modules/store';

// Auth types are re-exported from @hospital/shared
export type { LoginParams, LoginResult } from '@hospital/shared';
export type { PatientCreateData } from './modules/user';
export type { DepartmentListParams, DepartmentCreateData } from './modules/department';
export type { DoctorListParams, DoctorCreateData } from './modules/doctor';
export type { ScheduleListParams, ScheduleCreateData, ScheduleBatchCreateData, AvailableSchedule } from './modules/schedule';
export type { AppointmentListParams, AppointmentCreateData, AppointmentStatistics, PendingAppointment, CheckinQueueItem } from './modules/appointment';
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
  AppointmentSummary,
  StoreRankingItem,
} from './modules/statistics';

// Admin types
export type { 
  Admin, 
  Role, 
  Permission, 
  AdminLoginParams, 
  AdminLoginResult, 
  OnlineUser, 
  DeviceInfo, 
  UserStatus, 
  LoginHistory, 
  LoginHistoryResult,
  StoreInfo,
  MyStoresResult,
  SwitchStoreResult,
} from './modules/admin';

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
  PatientCreateData as PatientCreateDataAdmin,
  FamilyMemberCreateData,
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
  EmailConfig,
  ThumbnailSize,
  ImageConfig,
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
  ConsultationFeeTypeListParams,
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
  BatchOperateData,
  BatchOperateResult,
  CheckGeneratedResult,
  ScheduleGenerationLog,
  ScheduleTemplateCopyData,
  ScheduleTemplateCopyResult,
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

// Upload types
export type { UploadResult, TransferRequest, ThumbnailInfo, UploadOptions } from './modules/upload';

// Email Template types
export type {
  EmailTemplate,
  EmailTemplateListItem,
  EmailTemplateListParams,
  EmailTemplateCreateData,
  EmailTemplateUpdateData,
  EmailTestData,
  EmailTemplateType,
} from './modules/email-template';

// Favorite types
export type {
  Favorite,
  FavoriteTarget,
  FavoriteListResult,
  FavoriteCheckResult,
  FavoriteCreateData,
} from './modules/favorite';

// Booking Notice types
export type { 
  BookingNotice,
  BookingNoticeListResult,
  BookingNoticeCreateData,
  BookingNoticeUpdateData,
} from './modules/booking-notice';
