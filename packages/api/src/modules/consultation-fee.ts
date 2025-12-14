import request from '../request';
import type {
  ConsultationFeeType,
  ConsultationFeeTemplate,
  ConsultationFeeTemplateWithType,
  DoctorConsultationFee,
  DoctorConsultationFeeBatchCreate,
  DoctorFeeSettingResponse,
  StoreDepartmentFeeGroup,
} from '@hospital/shared';

// ========== 诊费类型 API ==========

export interface ConsultationFeeTypeCreateData {
  name: string;
  code?: string;
  description?: string;
  sortOrder?: number;
  status?: number;
}

export interface ConsultationFeeTypeUpdateData {
  name?: string;
  code?: string;
  description?: string;
  sortOrder?: number;
  status?: number;
}

export const consultationFeeTypeApi = {
  /**
   * 获取诊费类型列表
   */
  getList: (params?: { status?: number }): Promise<ConsultationFeeType[]> => {
    return request.get('/consultation-fees/types', { params });
  },

  /**
   * 获取诊费类型详情
   */
  getDetail: (id: string): Promise<ConsultationFeeType> => {
    return request.get(`/consultation-fees/types/${id}`);
  },

  /**
   * 创建诊费类型
   */
  create: (data: ConsultationFeeTypeCreateData): Promise<ConsultationFeeType> => {
    return request.post('/consultation-fees/types', data);
  },

  /**
   * 更新诊费类型
   */
  update: (id: string, data: ConsultationFeeTypeUpdateData): Promise<ConsultationFeeType> => {
    return request.put(`/consultation-fees/types/${id}`, data);
  },

  /**
   * 删除诊费类型
   */
  delete: (id: string): Promise<void> => {
    return request.delete(`/consultation-fees/types/${id}`);
  },
};

// ========== 诊费模板 API ==========

export interface ConsultationFeeTemplateCreateData {
  feeTypeId: string;
  initialFee: number;
  followUpFee: number;
  status?: number;
}

export const consultationFeeTemplateApi = {
  /**
   * 获取诊费模板列表（带类型信息）
   */
  getList: (): Promise<ConsultationFeeTemplateWithType[]> => {
    return request.get('/consultation-fees/templates');
  },

  /**
   * 创建或更新诊费模板
   */
  createOrUpdate: (data: ConsultationFeeTemplateCreateData): Promise<ConsultationFeeTemplate> => {
    return request.post('/consultation-fees/templates', data);
  },

  /**
   * 批量更新诊费模板
   */
  batchUpdate: (templates: ConsultationFeeTemplateCreateData[]): Promise<void> => {
    return request.put('/consultation-fees/templates', templates);
  },
};

// ========== 医生诊费配置 API ==========

export interface DoctorFeeQueryParams {
  storeId?: string;
  departmentId?: string;
}

export const doctorConsultationFeeApi = {
  /**
   * 获取医生诊费设置（包含是否使用模板）
   */
  getFeeSetting: (doctorId: string): Promise<DoctorFeeSettingResponse> => {
    return request.get(`/consultation-fees/doctors/${doctorId}`);
  },

  /**
   * 获取医生诊费配置（按门店-科室分组）
   */
  getFeesGrouped: (doctorId: string): Promise<StoreDepartmentFeeGroup[]> => {
    return request.get(`/consultation-fees/doctors/${doctorId}/grouped`);
  },

  /**
   * 更新医生是否使用诊费模板
   */
  updateUseTemplate: (doctorId: string, useFeeTemplate: number): Promise<void> => {
    return request.put(`/consultation-fees/doctors/${doctorId}/use-template`, {
      useFeeTemplate,
    });
  },

  /**
   * 获取医生诊费配置列表
   */
  getFees: (doctorId: string, params?: DoctorFeeQueryParams): Promise<DoctorConsultationFee[]> => {
    return request.get(`/consultation-fees/doctors/${doctorId}/fees`, { params });
  },

  /**
   * 批量保存医生诊费配置
   */
  batchSave: (doctorId: string, data: DoctorConsultationFeeBatchCreate): Promise<void> => {
    return request.post(`/consultation-fees/doctors/${doctorId}/fees/batch`, data);
  },

  /**
   * 删除医生在指定门店科室的所有诊费配置
   */
  deleteByStoreDepartment: (
    doctorId: string,
    storeId: string,
    departmentId: string
  ): Promise<void> => {
    return request.delete(`/consultation-fees/doctors/${doctorId}/fees/${storeId}/${departmentId}`);
  },
};
