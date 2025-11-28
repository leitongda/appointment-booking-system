import { request } from '../request';
import type { PageResult } from '@hospital/shared';

export interface PatientListItem {
  id: string;
  userId: string;
  name: string;
  phone: string;
  idCard: string;
  gender: number;
  birthday: string | null;
  relationship: string;
  isDefault: boolean;
  appointmentCount: number;
  noShowCount: number;
  isBlacklist: boolean;
  createdAt: string;
}

export interface PatientDetail extends PatientListItem {
  statistics: {
    appointmentCount: number;
    completedCount: number;
    noShowCount: number;
  };
  recentAppointments: {
    id: string;
    appointmentNo: string;
    status: number;
    createdAt: string;
  }[];
}

export interface PatientListParams {
  keyword?: string;
  isBlacklist?: boolean;
  page?: number;
  pageSize?: number;
}

const PREFIX = '/patients';

export const patientApi = {
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
};


