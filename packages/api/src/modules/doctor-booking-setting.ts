import request from '../request';
import type { DoctorBookingSetting, DoctorBookingSettingCreate, DoctorBookingSettingUpdate, PageResult } from '@hospital/shared';

export interface DoctorBookingSettingListParams {
  storeId?: string;
  doctorId?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

export const doctorBookingSettingApi = {
  /**
   * 获取医生预约设置列表
   */
  getList: (params?: DoctorBookingSettingListParams): Promise<PageResult<DoctorBookingSetting>> => {
    const queryParams = params ? {
      store_id: params.storeId,
      doctor_id: params.doctorId,
      status: params.status,
      page: params.page,
      page_size: params.pageSize,
    } : undefined;
    return request.get('/doctor-booking-settings', { params: queryParams });
  },

  /**
   * 获取医生预约设置详情
   */
  getDetail: (id: string): Promise<DoctorBookingSetting> => {
    return request.get(`/doctor-booking-settings/${id}`);
  },

  /**
   * 创建医生预约设置
   */
  create: (data: DoctorBookingSettingCreate): Promise<DoctorBookingSetting> => {
    return request.post('/doctor-booking-settings', data);
  },

  /**
   * 更新医生预约设置
   */
  update: (id: string, data: DoctorBookingSettingUpdate): Promise<DoctorBookingSetting> => {
    return request.put(`/doctor-booking-settings/${id}`, data);
  },

  /**
   * 删除医生预约设置
   */
  delete: (id: string): Promise<void> => {
    return request.delete(`/doctor-booking-settings/${id}`);
  },

  /**
   * 获取指定门店已配置的医生ID列表（用于禁用已配置的医生）
   */
  getExistingDoctorIds: (storeId: string): Promise<string[]> => {
    return request.get('/doctor-booking-settings/existing-doctors', {
      params: { store_id: storeId }
    });
  },

  /**
   * 更新医生预约设置状态
   */
  updateStatus: (id: string, status: number): Promise<void> => {
    return request.patch(`/doctor-booking-settings/${id}/status`, null, {
      params: { status }
    });
  },
};
