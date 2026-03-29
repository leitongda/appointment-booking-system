import { request } from '../request';
import type { PageResult } from '@hospital/shared';

// ========== 就诊卡列表项 ==========
export interface PatientListItem {
  id: string;
  userId: string;
  cardNo?: string;
  name: string;
  phone: string;
  idCard?: string;
  gender?: number;
  age?: number;
  birthday?: string | null;
  relationship?: string;
  isDefault: boolean;
  source?: number;
  appointmentCount: number;
  noShowCount: number;
  isBlacklist: boolean;
  totalConsumption?: number;
  createdAt: string;
  // 所属患者信息
  userPhone?: string;
  userNickname?: string;
}

// ========== 患者统计 ==========
export interface PatientStatistics {
  appointmentCount: number;
  completedCount: number;
  noShowCount: number;
}

// ========== 患者详情 ==========
export interface PatientDetail {
  // 基本信息
  id: string;
  userId: string;
  cardNo?: string;
  name: string;
  phone: string;
  gender?: number;
  province?: string;
  city?: string;
  district?: string;
  street?: string;
  idCardType: number;
  idCard?: string;
  ethnicity: string;
  birthday?: string | null;
  age?: number;
  relationship?: string;
  address?: string;
  source: number;
  totalConsumption: number;
  lastVisitDate?: string | null;
  isBlacklist: boolean;
  createdAt: string;
  
  // 用户信息
  nickname?: string;
  points: number;
  
  // 统计信息
  statistics: PatientStatistics;
  
  // 家庭成员
  familyMembers: PatientListItem[];
}

// ========== 患者更新数据 ==========
export interface PatientUpdateData {
  name?: string;
  phone?: string;
  idCard?: string;
  gender?: number;
  relationship?: string;
  isDefault?: boolean;
  province?: string;
  city?: string;
  district?: string;
  street?: string;
  idCardType?: number;
  ethnicity?: string;
  address?: string;
}

// ========== 预约记录 ==========
export interface PatientAppointment {
  id: string;
  appointmentNo: string;
  storeName?: string;
  departmentName?: string;
  doctorId?: string;
  doctorName?: string;
  scheduleDate?: string;
  startTime?: string;
  endTime?: string;
  queueNumber?: number;
  status: number;
  isAdminBooked: boolean;
  isFollowUp: boolean;
  createdAt: string;
}

export interface PatientAppointmentParams {
  doctorId?: string;
  startDate?: string;
  endDate?: string;
  status?: number;
  isAdminBooked?: boolean;
  isFollowUp?: boolean;
  page?: number;
  pageSize?: number;
}

// ========== 消费/项目记录 ==========
export interface ConsumptionRecord {
  id: string;
  orderNo: string;
  storeName?: string;
  itemName: string;
  scheduleDate?: string;
  startTime?: string;
  endTime?: string;
  status: number;
  createdAt: string;
}

export interface ConsumptionRecordParams {
  itemName?: string;
  page?: number;
  pageSize?: number;
}

// ========== 积分相关 ==========
export interface PointLog {
  id: string;
  userId: string;
  changeAmount: number;
  balance: number;
  type: number;
  remark?: string;
  operatorId?: string;
  operatorName?: string;
  createdAt: string;
}

export interface PointLogResult extends PageResult<PointLog> {
  currentPoints: number;
}

export interface PointAdjustData {
  amount: number;
  remark: string;
}

export interface PointAdjustResult extends PointLog {
  currentPoints: number;
}

export interface PointSummary {
  currentPoints: number;
  totalEarned: number;
  totalSpent: number;
}

// ========== 查询参数 ==========
export interface PatientListParams {
  keyword?: string;
  isBlacklist?: boolean;
  page?: number;
  pageSize?: number;
}

// ========== 创建患者 ==========
export interface PatientCreateData {
  name: string;
  phone: string;
  idCard?: string;
  gender?: number;
  birthday?: string;
  relationship?: string;
  isDefault?: boolean;
  province?: string;
  city?: string;
  district?: string;
  street?: string;
  idCardType?: number;
  ethnicity?: string;
  address?: string;
}

// ========== 添加家庭成员 ==========
export interface FamilyMemberCreateData {
  name: string;
  phone: string;
  idCard?: string;
  gender?: number;
  birthday?: string;
  relationship?: string;
  isDefault?: boolean;
  province?: string;
  city?: string;
  district?: string;
  street?: string;
  idCardType?: number;
  ethnicity?: string;
  address?: string;
}

const PREFIX = '/patients';

export const patientApi = {
  /**
   * 创建患者（管理员手动添加）
   */
  create: (data: PatientCreateData): Promise<PatientDetail> => {
    return request.post(PREFIX, data);
  },

  /**
   * 获取患者列表
   */
  getList: (params?: PatientListParams): Promise<PageResult<PatientListItem>> => {
    return request.get(PREFIX, { params });
  },

  /**
   * 获取患者详情
   */
  getDetail: (id: string): Promise<PatientDetail> => {
    return request.get(`${PREFIX}/${id}`);
  },

  /**
   * 更新患者信息
   */
  update: (id: string, data: PatientUpdateData): Promise<PatientDetail> => {
    return request.put(`${PREFIX}/${id}`, data);
  },

  /**
   * 删除患者（就诊卡）
   */
  delete: (id: string): Promise<{ message: string }> => {
    return request.delete(`${PREFIX}/${id}`);
  },

  /**
   * 获取患者预约记录
   */
  getAppointments: (id: string, params?: PatientAppointmentParams): Promise<PageResult<PatientAppointment>> => {
    return request.get(`${PREFIX}/${id}/appointments`, { params });
  },

  /**
   * 获取患者消费/项目记录
   */
  getConsumptionRecords: (id: string, params?: ConsumptionRecordParams): Promise<PageResult<ConsumptionRecord>> => {
    return request.get(`${PREFIX}/${id}/consumption-records`, { params });
  },

  /**
   * 获取积分流水
   */
  getPointLogs: (id: string, params?: { page?: number; pageSize?: number }): Promise<PointLogResult> => {
    return request.get(`${PREFIX}/${id}/points`, { params });
  },

  /**
   * 调整积分
   */
  adjustPoints: (id: string, data: PointAdjustData): Promise<PointAdjustResult> => {
    return request.post(`${PREFIX}/${id}/points`, data);
  },

  /**
   * 获取积分汇总
   */
  getPointSummary: (id: string): Promise<PointSummary> => {
    return request.get(`${PREFIX}/${id}/points/summary`);
  },

  /**
   * 获取黑名单列表
   */
  getBlacklist: (params?: { page?: number; pageSize?: number }): Promise<PageResult<PatientListItem>> => {
    return request.get(`${PREFIX}/blacklist`, { params });
  },

  /**
   * 加入黑名单
   */
  addToBlacklist: (id: string, reason?: string): Promise<void> => {
    return request.put(`${PREFIX}/${id}/blacklist`, { reason });
  },

  /**
   * 移出黑名单
   */
  removeFromBlacklist: (id: string): Promise<void> => {
    return request.delete(`${PREFIX}/${id}/blacklist`);
  },

  /**
   * 添加家庭成员（亲友）
   */
  addFamilyMember: (patientId: string, data: FamilyMemberCreateData): Promise<PatientListItem> => {
    return request.post(`${PREFIX}/${patientId}/family-members`, data);
  },

  /**
   * 编辑家庭成员
   */
  updateFamilyMember: (patientId: string, memberId: string, data: PatientUpdateData): Promise<PatientListItem> => {
    return request.put(`${PREFIX}/${patientId}/family-members/${memberId}`, data);
  },

  /**
   * 删除家庭成员
   */
  deleteFamilyMember: (patientId: string, memberId: string): Promise<void> => {
    return request.delete(`${PREFIX}/${patientId}/family-members/${memberId}`);
  },
};
