/**
 * Settings 各 tab 的默认值常量。
 *
 * 与后端 DEFAULT_SETTINGS 保持一致，用于表单 initialValues 的 fallback。
 * 从 settings.tsx 抽取，避免 1474 行文件的"常量洪水"。
 */
import type {
  BookingSettings,
  PatientCardConfig,
  EmailConfig,
  ImageConfig,
  SmsConfig,
  SecurityConfig,
  SourceReleaseConfig,
} from '@hospital/api';

/** 预约设置默认值（与后端 DEFAULT_SETTINGS 保持一致） */
export const DEFAULT_BOOKING_SETTINGS: BookingSettings = {
  advanceDays: 10,
  sameDayBooking: true,
  cancelHours: 2,
  perDayLimit: 3,
  perDoctorLimit: 1,
  noShowLimit: 3,
  blacklistDays: 30,
  advanceBookingMinutes: 0,
  advanceBookingDirection: 'before',
  advanceBookingReference: 'end',
  signInAdvanceMinutes: 30,
  signInLateMinutes: 30,
  appointmentReminderHours: 24,
};

/** 就诊卡配置默认值 */
export const DEFAULT_PATIENT_CARD_CONFIG: PatientCardConfig = {
  cardName: '就诊卡',
  cardDescription: '',
  maxCardsPerUser: 5,
  showOnHomepage: false,
};

/** 邮件配置默认值 */
export const DEFAULT_EMAIL_CONFIG: EmailConfig = {
  smtpHost: '',
  smtpPort: 465,
  smtpUser: '',
  smtpPassword: '',
  smtpSsl: true,
  senderName: '',
  senderEmail: '',
};

/** 图片配置默认值 */
export const DEFAULT_IMAGE_CONFIG: ImageConfig = {
  thumbnailSizes: [
    { name: 'small', width: 200, height: 200 },
    { name: 'medium', width: 800, height: 800 },
  ],
  compressQuality: 85,
};

/** 短信通知策略默认值 */
export const DEFAULT_SMS_POLICY: Pick<SmsConfig, 'codeExpireSeconds' | 'sendIntervalSeconds'> = {
  codeExpireSeconds: 300,
  sendIntervalSeconds: 60,
};

/** 安全策略默认值 */
export const DEFAULT_SECURITY_CONFIG: SecurityConfig = {
  accessTokenExpireMinutes: 30,
  refreshTokenExpireDays: 7,
  defaultPassword: '********',
  rateLimitPerMinute: 300,
  rateLimitPerSecond: 50,
  loginFailureLockCount: 5,
  sessionTimeoutMinutes: 120,
};

/** 号源释放策略默认值 */
export const DEFAULT_SOURCE_RELEASE_CONFIG: SourceReleaseConfig = {
  lockTimeoutMinutes: 15,
  batchReleaseEnabled: false,
  batchReleaseDays: 7,
  batchReleaseTime: '08:00',
  autoCancelUnpaidMinutes: 30,
  noShowAutoMarkHours: 24,
  allowOverbooking: false,
  overbookingLimit: 0,
};
