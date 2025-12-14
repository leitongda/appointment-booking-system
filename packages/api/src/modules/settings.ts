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
};


