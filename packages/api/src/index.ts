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

// 导出 Tauri 桌面壳分支（仅 window.__TAURI__ 存在时生效，web 端零变化）
export { isTauriDesktop, isTauriPackaged, applyDesktopBaseUrl } from './desktop';
export type { DesktopConfig } from './desktop';

// 导出共享错误处理工具
export {
  ERROR_MESSAGES,
  getRequestPath,
  shouldAddToken,
  DEFAULT_EXCLUDE_TOKEN_PATHS,
  handleStructuredErrorCode,
  isRsaDecryptError,
  handleNetworkError,
} from './utils/error-handling';
export type { ErrorHandlingDeps } from './utils/error-handling';

// 导出 Web 拦截器工厂（admin / doctor / patient-h5 三端 request.ts 共享骨架）
export { createWebInterceptors } from './web-interceptors';
export type {
  WebInterceptorOptions,
  WebInterceptorDeps,
  WebInterceptors,
  UnauthorizedContext,
  TenantSuspendedContext,
  RawAxiosErrorRenderer,
} from './web-interceptors';

// 导出性能监控和重试工具
export {
  getPerformanceMonitor,
  createApiTimer,
  getPerformanceSummary,
  clearPerformanceData,
} from './utils/performance';
export type { PerformanceMetrics, PerformanceSummary, ApiTimer } from './utils/performance';

export {
  setupRetryInterceptor,
  withRetry,
  getRetryStats,
} from './utils/retry';
export type { RetryOptions, RetryStats } from './utils/retry';

// 导出请求适配器（用于小程序等非浏览器环境）
export { createTaroAdapter, getTaroToken, setTaroToken } from './adapters';
// NOTE: 旧的全局 API 配置模块 (config.ts) 已移除 —— 请改用 setBaseURL/getBaseURL。
export type { TaroAdapterConfig } from './adapters';

// 导出 RSA 加密工具
export { rsaEncrypt, setPublicKey, getPublicKey, clearPublicKey } from './modules/crypto';

// 导出共享 React Hooks（邮箱绑定 / 通用倒计时等）
export { useCountdown, useEmailBinding } from './hooks';
export type {
  UseCountdownResult,
  EmailBindingMode,
  EmailBindingApi,
  UseEmailBindingOptions,
  UseEmailBindingResult,
} from './hooks';

// 导出 API 模块
export { authApi } from './modules/auth';
export { accountApi } from './modules/account';
export { userApi } from './modules/user';
export { departmentApi } from './modules/department';
export { doctorApi } from './modules/doctor';
export { doctorReviewApi } from './modules/doctor-reviews';
export type {
  DoctorReviewItem,
  DoctorReviewPageResult,
  DoctorReviewListParams,
  DoctorReviewCreateData,
} from './modules/doctor-reviews';
export { scheduleApi } from './modules/schedule';
export { appointmentApi } from './modules/appointment';
export { doctorQueueApi } from './modules/doctor-portal-queue';
export { attendanceApi } from './modules/attendance';
export type {
  CheckInData,
  CheckOutData,
  AttendanceRecord,
  AttendanceRecordListParams,
  DailyStat,
  AttendanceShift,
  AttendanceShiftCreateData,
  AttendanceShiftUpdateData,
  AttendanceGroup,
  AttendanceGroupCreateData,
  AttendanceGroupUpdateData,
  GroupMember,
  AttendanceRule,
  AttendanceRuleCreateData,
  AttendanceRuleUpdateData,
  LeaveType,
} from './modules/attendance';
export { medicalRecordApi } from './modules/medical-record';
export { contentApi } from './modules/content';
export { siteApi, categoryApi, articleApi } from './modules/cms';
export { commonServiceApi } from './modules/common-service';
export type { CommonServiceItem, CommonServiceListResponse, HealthReminderConfig, UserHealthReminder } from './modules/common-service';
export { statisticsApi } from './modules/statistics';
export { platformMetricsApi } from './modules/platform-metrics';
export type {
  PlatformOverviewData,
  TenantCompareItem,
  StoreCompareItem,
  PlatformTrendPoint,
  PlatformMetricsQuery,
  StoreCompareQuery,
} from './modules/platform-metrics';
export { adminApi } from './modules/admin';
export { settingsApi } from './modules/settings';
export { integrationApi } from './modules/integration';
export type {
  IntegrationProvider,
  IntegrationConfig,
  IntegrationUpsertInput,
  ProviderInfo as IntegrationProviderInfo,
  IntegrationBinding,
  TestConnectionResult,
} from './modules/integration';
export { patientApi } from './modules/patient';
export { storeApi } from './modules/store';
export { messageApi } from './modules/message';
export { leaveRequestApi } from './modules/leave-request';
export { feedbackApi } from './modules/feedback';
export { knowledgeApi } from './modules/knowledge';
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
export { pointApi } from './modules/point';
export { uploadApi } from './modules/upload';
export { examinationReportApi } from './modules/examination-report';
export { followUpApi, selfReportApi } from './modules/follow-up';
export { freelancerApi, freelanceTaskApi, freelanceSettlementApi } from './modules/freelance';
export type {
  Freelancer,
  FreelancerCreateData,
  FreelancerUpdateData,
  FreelanceTask,
  FreelanceTaskCreateData,
  FreelanceTaskUpdateData,
  FreelanceInteraction,
  FreelanceInteractionCreateData,
  FreelanceSettlement,
  FreelanceSettlementItem,
  FreelanceListParams,
  FreelanceTaskListParams,
  FreelanceSettlementListParams,
} from './modules/freelance';
export { emailTemplateApi } from './modules/email-template';
export { dataApi } from './modules/data';
export type { ImportResult } from './modules/data';
export { userManageApi } from './modules/user-manage';
export { favoriteApi } from './modules/favorite';
export { bookingNoticeApi } from './modules/booking-notice';
export { storeVisitTypeConfigApi } from './modules/store-visit-type-config';
export { ruleSetApi, shiftTypeApi } from './modules/rule-set';
export { auditLogApi } from './modules/audit-log';
export { storeEmailRecipientApi } from './modules/store-email-recipient';
export { tenantApi } from './modules/tenant';
export { analyticsApi } from './modules/analytics';
export type { BehaviorLog, BehaviorLogListParams, BehaviorOverview, TenantActivity, DailyBehaviorItem, DailyActivityItem } from './modules/analytics';
export { miniappPlatformApi } from './modules/miniapp-platform';
export { marketingApi, getPosterQrcode } from './modules/marketing';
export type { PosterQrcodeParams, PosterQrcodeResult } from './modules/marketing';
export { notificationLogApi } from './modules/notification-log';
export { notificationPreferenceApi } from './modules/notification-preference';
export { paymentApi } from './modules/payment';
export { refundApi } from './modules/refund';
export { waitlistApi } from './modules/waitlist';
export { platformAnnouncementApi } from './modules/platform-announcement';
export type { PlatformAnnouncement, PlatformAnnouncementCreateData, PlatformAnnouncementListParams } from './modules/platform-announcement';
export { supportTicketApi } from './modules/support-ticket';
export type { SupportTicket, SupportTicketCreateData, SupportTicketUpdateData, SupportTicketListParams, SupportTicketStatistics } from './modules/support-ticket';
export { approvalInstanceApi, approvalFlowApi } from './modules/approval';
export type { FlowDefinitionCreateData } from './modules/approval';
export { dictApi } from './modules/dict';
export { amapApi } from './modules/amap';
export { backupApi } from './modules/backup';
export type { BackupPrecheckResult, BackupImportResult } from './modules/backup';
export type { AmapPoi, AmapGeocode, AmapRegeoResult } from './modules/amap';
export type {
  DictTypeItem,
  DictItemData,
  DictTypeListParams,
  DictTypeCreateData,
  DictTypeUpdateData,
  DictItemCreateData,
  DictItemUpdateData,
  DictOptionItem,
  DictOptionsResponse,
  SortItemData,
} from './modules/dict';
export type {
  WaitlistEntry,
  WaitlistStatus,
  JoinWaitlistParams,
  MyWaitlistParams,
  WaitlistPageResult,
  WaitlistStats,
  WaitlistListParams,
} from './modules/waitlist';
export type {
  UserListItem,
  UserDetail,
  UserCard,
  UserListParams,
  UserUpdateData,
  CardCreateData,
  CardUpdateData,
} from './modules/user-manage';
export type { NotificationLog, NotificationLogListParams, NotificationLogStats } from './modules/notification-log';
export type { NotificationPreference } from './modules/notification-preference';

// Payment & Refund types
export type { PaymentOrderStatus } from './modules/payment';
export type { RefundRecordItem, RefundListParams, RefundListResult, RefundableAmount, RefundCreateData } from './modules/refund';

// Store types
export type { StoreAdmin } from './modules/store';

// Auth types are re-exported from @hospital/shared
export type { LoginParams, LoginResult } from '@hospital/shared';
export type { LeaveRequest, LowCodePage } from '@hospital/shared';
export type {
  WechatLoginResponse,
  AccountInfo,
  RoleType,
  AdminAccountInfo,
  DoctorAccountInfo,
  UserAccountInfo,
} from './modules/auth';
export type { PatientCreateData } from './modules/user';
export type { DepartmentListParams, DepartmentCreateData, SymptomMatchResult } from './modules/department';
export type { DoctorListParams, DoctorCreateData } from './modules/doctor';
export type { ScheduleListParams, ScheduleCreateData, ScheduleBatchCreateData, AvailableSchedule } from './modules/schedule';
export type { AppointmentListParams, AppointmentCreateData, AppointmentStatistics, PendingAppointment, CheckinQueueItem, PatientHistoryItem, RefundRecord } from './modules/appointment';
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
  StoreDashboardStats,
  RetentionItem,
  RevisitRateData,
} from './modules/statistics';

// Admin types
export type {
  Admin,
  TenantStatusInfo,
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
  AccountStatsSummary,
  DeviceDistribution,
  HourlyDistribution,
  AccountStatsDetail,
  AccountStatsResponse,
  AccountStatsQueryParams,
  IntegrationLoginProvider,
  IntegrationQrcodeResult,
  IntegrationLoginResult,
  IntegrationBindPhoneParams,
  IntegrationBindingItem,
} from './modules/admin';

// Content types
export type { Banner, News, Notice } from './modules/content';
// CMS types
export type {
  CmsSite,
  CmsSiteCreateData,
  CmsSiteUpdateData,
  CmsCategory,
  CmsCategoryTreeNode,
  CmsCategoryCreateData,
  CmsCategoryUpdateData,
  CmsArticle,
  CmsArticleCreateData,
  CmsArticleUpdateData,
} from './modules/cms';

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
  TimePeriodConfig,
  SecurityConfig,
  SourceReleaseConfig,
} from './modules/settings';

// Blacklist types
export type {
  BlacklistItem,
  BlacklistListParams,
  BlacklistCreateData,
  BlacklistCheckResult,
} from './modules/blacklist';

// Point types
export type {
  PointLogItem,
  PointUserItem,
  PointAdjustData as PointAdjustDataPoint,
  PointLogParams,
  PointUserParams,
} from './modules/point';

// Admin Operation Log type
export type { OperationLog } from './modules/admin';

// Knowledge base (RAG) types
export type {
  KnowledgeBase,
  KnowledgeBaseCreateData,
  KnowledgeBaseListParams,
  KnowledgeBaseScope,
  KnowledgeChunk,
  KnowledgeDocStatus,
  KnowledgeDocument,
  KnowledgeDocumentListParams,
  KnowledgeDocumentUpdateData,
  KnowledgeFailedStage,
  KnowledgeFolder,
  KnowledgeFolderCreateData,
  KnowledgeFolderUpdateData,
  KnowledgePermission,
  KnowledgeSearchHit,
  KnowledgeSearchParams,
  KnowledgeSearchResult,
  KnowledgeShare,
  KnowledgeShareCreateData,
  KnowledgeShareGrantee,
  KnowledgeSharePermission,
  KnowledgeVisibility,
} from './modules/knowledge';

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
  CrossStoreDoctorMapping,
  ScheduleTemplateCrossStoreCopyData,
  ScheduleTemplateCrossStoreCopyResult,
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
  ProcessingMethod,
  ProcessingStatus,
  SuspensionProcessResult,
} from './modules/schedule-suspension';

// Schedule Statistics types
export type {
  ScheduleStatisticsItem,
  ScheduleStatisticsResponse,
  ScheduleStatisticsParams,
  UtilizationTrendItem,
  UtilizationTrendResponse,
  DoctorWorkloadItem,
  DoctorWorkloadResponse,
  PeakHourCell,
  PeakHourHeatmapResponse,
} from './modules/schedule';

// Upload types
export type { UploadResult, TransferRequest, ThumbnailInfo, UploadOptions } from './modules/upload';

// Examination Report types
export type { ExaminationReport, ExaminationReportListItem, ExaminationReportUploadParams } from './modules/examination-report';

// Follow-Up types
export type {
  FollowUpPlan, FollowUpPlanListItem, FollowUpPlanStep,
  FollowUpPlanCreateData, FollowUpPlanUpdateData,
  FollowUpTask, FollowUpTaskListItem,
  FollowUpTaskCreateData, FollowUpTaskGenerateData,
  FollowUpRecord, FollowUpRecordListItem,
  FollowUpRecordCreateData, FollowUpRecordUpdateData,
  FollowUpStatistics,
  SelfReportCreateData, SelfReportListItem, SelfReportDetail,
} from './modules/follow-up';

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

// Rule Set types
export type {
  RuleSet,
  RuleWindow,
  RuleBookingPolicy,
  RuleCheckinPolicy,
  RuleCapacityPolicy,
  ShiftType,
  RulePreviewRequest,
  RulePreviewResponse,
  RuleSetBrief,
  WindowCheckResult,
  WindowOffsetConfig,
  RuleSetListParams,
  RuleSetCreateData,
  RuleSetUpdateData,
  RuleWindowCreateData,
  RuleWindowUpdateData,
  RuleSetPresetResponse,
  RuleSetPresetCreateData,
} from './modules/rule-set';

// Store Email Recipient types
export type {
  StoreEmailRecipient,
  StoreEmailRecipientListParams,
  StoreEmailRecipientCreateData,
  StoreEmailRecipientUpdateData,
  EventTypeOption,
} from './modules/store-email-recipient';

// Tenant types
export type {
  SubscriptionPlan,
  SubscriptionPlanCreateData,
  SubscriptionPlanUpdateData,
  Tenant,
  TenantListParams,
  TenantCreateData,
  TenantUpdateData,
  TenantSelfUpdateData,
  TenantSubscription,
  TenantSubscriptionCreateData,
  TenantUsageLog,
  TenantUsageSummary,
  CurrentTenant,
  CurrentTenantPublic,
  TenantNotification,
  TenantNotificationList,
  TenantSelfRegisterData,
  TenantSelfRegisterResult,
  TenantTag,
  MigrationPrecheckResult,
  MigrationExecuteData,
  MigrationResult,
  PasswordPolicy,
  TenantUsageTrend,
} from './modules/tenant';

// Miniapp Platform types
export type {
  Company,
  CompanyCreateData,
  CompanyUpdateData,
  CompanyListParams,
  PaymentProfile,
  PaymentProfileCreateData,
  PaymentProfileUpdateData,
  PaymentProfileListParams,
  MiniappInstance,
  MiniappInstanceCreateData,
  MiniappInstanceUpdateData,
  MiniappInstanceListParams,
  AppTemplate,
  AppTemplateCreateData,
  AppTemplateUpdateData,
  AppTemplateListParams,
  TemplateVersion,
  TemplateVersionCreateData,
  BuildJob,
  BuildJobCreateData,
  BuildJobListParams,
  ReleaseJob,
  ReleaseJobCreateData,
  ReleaseJobListParams,
} from './modules/miniapp-platform';

// LowCode types
export { lowcodeApi } from './modules/lowcode';
export type {
  LowCodePageListParams,
  DataSourceTestRequest,
  DataSourceTestResponse,
  DataSourceFieldSuggestion,
  DeployStatus,
  DeployStatusResponse,
  DeployTriggerResponse,
  PreviewQrResponse,
  RollbackDeployResponse,
  DeployHistoryItem,
  VersionItem,
  VersionListResponse,
} from './modules/lowcode';

// LowCode Template Marketplace
export { lowcodeTemplateApi } from './modules/lowcode-template';
export type { TemplateVersionCreateData as LowCodeTemplateVersionCreateData } from './modules/lowcode-template';

export type {
  LowCodeTemplate,
  LowCodeTemplateCreateData,
  LowCodeTemplateUpdateData,
  LowCodeTemplateListParams,
  LowCodeTemplateVersionItem,
  LowCodeTemplateVersionListResponse,
  LowCodeTemplateCategoryItem,
  LowCodeTemplateForkResponse,
} from '@hospital/shared';

// 操作指引
export { guideToursApi } from './modules/guide-tours';
export type { GuideTourItem, TourStep, GuideTourProgress, LocaleMap } from './modules/guide-tours';

export { adminGuideToursApi } from './modules/admin-guide-tours';
export type { GuideTourDetail, GuideTourListItem, GuideTourFormData } from './modules/admin-guide-tours';
