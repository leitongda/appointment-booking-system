import { request } from '../request';

// 预约设置
export interface BookingSettings {
  advanceDays: number;
  sameDayBooking: boolean;
  cancelHours: number;
  perDayLimit: number;
  perDoctorLimit: number;
  noShowLimit: number;
  blacklistDays: number;
}

// 医院信息
export interface HospitalInfo {
  hospitalName: string;
  hospitalLevel: string;
  address: string;
  phone: string;
  workTime: string;
  introduction: string;
  logo: string;
}

// 微信配置
export interface WechatConfig {
  appId: string;
  appSecret: string;
  mchId: string;
  apiKey: string;
  notifyUrl: string;
}

// 短信配置
export interface SmsConfig {
  smsProvider: string;
  accessKeyId: string;
  accessKeySecret: string;
  signName: string;
  templateCode: string;
}

// 预约规则（公开）
export interface BookingRules {
  advanceDays: number;
  sameDayBooking: boolean;
  cancelHours: number;
  perDayLimit: number;
}

// 预约选项配置
export interface BookingFieldConfig {
  field: string;
  name: string;
  enabled: boolean;
  required: boolean;
}

// 就诊卡配置
export interface PatientCardConfig {
  cardName: string;
  cardDescription: string;
  maxCardsPerUser: number;
  showOnHomepage: boolean;
}

// 邮件配置
export interface EmailConfig {
  smtpHost: string;
  smtpPort: number;
  smtpUser: string;
  smtpPassword: string;
  smtpSsl: boolean;
  senderName: string;
  senderEmail: string;
}

// 缩略图尺寸配置
export interface ThumbnailSize {
  name: string;
  width: number;
  height: number;
}

// 图片处理配置
export interface ImageConfig {
  thumbnailSizes: ThumbnailSize[];
  compressQuality: number;
}

// 时段配置
export interface TimePeriodConfig {
  key: string;       // 时段标识，如 morning, afternoon
  name: string;      // 时段名称，如 上午, 下午
  startTime: string; // 开始时间，格式 HH:mm
  endTime: string;   // 结束时间，格式 HH:mm
}

// 时段配置响应
export interface TimePeriodsResponse {
  periods: TimePeriodConfig[];
  isCustom: boolean;  // 是否为门店自定义配置
}

const PREFIX = '/settings';

export const settingsApi = {
  // ========== 预约设置 ==========
  getBookingSettings: (): Promise<BookingSettings> => {
    return request.get(`${PREFIX}/booking`);
  },

  updateBookingSettings: (data: Partial<BookingSettings>): Promise<void> => {
    return request.put(`${PREFIX}/booking`, data);
  },

  // 公开接口：获取预约规则
  getBookingRules: (): Promise<BookingRules> => {
    return request.get(`${PREFIX}/booking/rules`);
  },

  // ========== 医院信息 ==========
  getHospitalInfo: (): Promise<HospitalInfo> => {
    return request.get(`${PREFIX}/hospital`);
  },

  updateHospitalInfo: (data: Partial<HospitalInfo>): Promise<void> => {
    return request.put(`${PREFIX}/hospital`, data);
  },

  // ========== 微信配置 ==========
  getWechatConfig: (): Promise<WechatConfig> => {
    return request.get(`${PREFIX}/wechat`);
  },

  updateWechatConfig: (data: Partial<WechatConfig>): Promise<void> => {
    return request.put(`${PREFIX}/wechat`, data);
  },

  // ========== 短信配置 ==========
  getSmsConfig: (): Promise<SmsConfig> => {
    return request.get(`${PREFIX}/sms`);
  },

  updateSmsConfig: (data: Partial<SmsConfig>): Promise<void> => {
    return request.put(`${PREFIX}/sms`, data);
  },

  // ========== 预约选项配置 ==========
  getBookingFields: (): Promise<BookingFieldConfig[]> => {
    return request.get(`${PREFIX}/booking-fields`);
  },

  updateBookingFields: (fields: BookingFieldConfig[]): Promise<{ data: BookingFieldConfig[] }> => {
    return request.put(`${PREFIX}/booking-fields`, { fields });
  },

  // ========== 就诊卡配置 ==========
  getPatientCardConfig: (): Promise<PatientCardConfig> => {
    return request.get(`${PREFIX}/patient-card`);
  },

  updatePatientCardConfig: (data: Partial<PatientCardConfig>): Promise<{ data: PatientCardConfig }> => {
    return request.put(`${PREFIX}/patient-card`, data);
  },

  // ========== 邮件配置 ==========
  getEmailConfig: (): Promise<EmailConfig> => {
    return request.get(`${PREFIX}/email`);
  },

  updateEmailConfig: (data: Partial<EmailConfig>): Promise<void> => {
    return request.put(`${PREFIX}/email`, data);
  },

  // ========== 图片处理配置 ==========
  getImageConfig: (): Promise<ImageConfig> => {
    return request.get(`${PREFIX}/image`);
  },

  updateImageConfig: (data: Partial<ImageConfig>): Promise<{ data: ImageConfig }> => {
    return request.put(`${PREFIX}/image`, data);
  },

  // ========== 时段配置 ==========
  /**
   * 获取时段配置
   * @param storeId 门店ID，不传则获取全局配置
   */
  getTimePeriods: (storeId?: string): Promise<TimePeriodsResponse> => {
    const params = storeId ? { storeId } : {};
    return request.get(`${PREFIX}/time-periods`, { params });
  },

  /**
   * 更新时段配置
   * @param periods 时段配置列表
   * @param storeId 门店ID，不传则更新全局配置
   */
  updateTimePeriods: (periods: TimePeriodConfig[], storeId?: string): Promise<{ data: { periods: TimePeriodConfig[] } }> => {
    return request.put(`${PREFIX}/time-periods`, { periods, storeId });
  },

  /**
   * 删除门店自定义时段配置（恢复使用全局配置）
   * @param storeId 门店ID
   */
  deleteStoreTimePeriods: (storeId: string): Promise<{ message: string }> => {
    return request.delete(`${PREFIX}/time-periods/${storeId}`);
  },
};


