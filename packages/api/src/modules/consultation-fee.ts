import request from '../request';
import type {
  ConsultationFeeType,
  ConsultationFeeTypeCreate,
  ConsultationFeeTypeUpdate,
  ConsultationFeeTemplate,
  ConsultationFeeTemplateWithType,
  StoreFeeTemplateWithType,
  StoreFeeTemplateBatchCreate,
  DoctorConsultationFee,
  DoctorConsultationFeeBatchCreate,
  DoctorFeeSettingResponse,
  StoreDepartmentFeeGroup,
  ApplyTemplateRequest,
} from '@hospital/shared';

// ========== 诊费类型 API ==========

export interface ConsultationFeeTypeListParams {
  status?: number;
  storeId?: string;  // 门店ID，获取门店可用的诊费类型（全局+门店专属）
  includeGlobal?: boolean;  // 是否包含全局类型
}

export const consultationFeeTypeApi = {
  /**
   * 获取诊费类型列表
   * @param params.storeId 门店ID，不传则返回全局类型，传则返回门店可用类型（全局+门店专属）
   * @param params.includeGlobal 是否包含全局类型，默认true
   */
  getList: (params?: ConsultationFeeTypeListParams): Promise<ConsultationFeeType[]> => {
    return request.get('/consultation-fees/types', { params });
  },

  /**
   * 获取门店可用的诊费类型（全局类型 + 门店专属类型）
   */
  getStoreAvailableTypes: (storeId: string, status?: number): Promise<ConsultationFeeType[]> => {
    return request.get('/consultation-fees/types', {
      params: { storeId, status, includeGlobal: true },
    });
  },

  /**
   * 获取诊费类型详情
   */
  getDetail: (id: string): Promise<ConsultationFeeType> => {
    return request.get(`/consultation-fees/types/${id}`);
  },

  /**
   * 创建诊费类型
   * @param data.storeId 门店ID，不传则创建全局类型
   */
  create: (data: ConsultationFeeTypeCreate): Promise<ConsultationFeeType> => {
    return request.post('/consultation-fees/types', data);
  },

  /**
   * 更新诊费类型
   */
  update: (id: string, data: ConsultationFeeTypeUpdate): Promise<ConsultationFeeType> => {
    return request.put(`/consultation-fees/types/${id}`, data);
  },

  /**
   * 删除诊费类型
   */
  delete: (id: string): Promise<void> => {
    return request.delete(`/consultation-fees/types/${id}`);
  },
};

// ========== 全局诊费模板 API ==========

export interface ConsultationFeeTemplateCreateData {
  feeTypeId: string;
  initialFee: number;
  followUpFee: number;
  status?: number;
}

export const consultationFeeTemplateApi = {
  /**
   * 获取全局诊费模板列表（带类型信息）
   */
  getList: (): Promise<ConsultationFeeTemplateWithType[]> => {
    return request.get('/consultation-fees/templates');
  },

  /**
   * 创建或更新全局诊费模板
   */
  createOrUpdate: (data: ConsultationFeeTemplateCreateData): Promise<ConsultationFeeTemplate> => {
    return request.post('/consultation-fees/templates', data);
  },

  /**
   * 批量更新全局诊费模板
   */
  batchUpdate: (templates: ConsultationFeeTemplateCreateData[]): Promise<void> => {
    return request.put('/consultation-fees/templates', templates);
  },
};

// ========== 门店诊费模板 API ==========

export const storeFeeTemplateApi = {
  /**
   * 获取门店诊费模板列表（带类型信息）
   * 返回门店可用的所有诊费类型及其模板配置，包含全局模板金额作为参考
   */
  getList: (storeId: string): Promise<StoreFeeTemplateWithType[]> => {
    return request.get(`/consultation-fees/store-templates/${storeId}`);
  },

  /**
   * 批量保存门店诊费模板
   */
  batchSave: (storeId: string, data: StoreFeeTemplateBatchCreate): Promise<void> => {
    return request.post(`/consultation-fees/store-templates/${storeId}/batch`, data);
  },

  /**
   * 删除门店诊费模板
   */
  delete: (storeId: string, feeTypeId: string): Promise<void> => {
    return request.delete(`/consultation-fees/store-templates/${storeId}/${feeTypeId}`);
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
   * 一键带入模板：将门店模板的金额应用到医生诊费配置
   * 优先使用门店模板，如果门店未配置则使用全局模板
   */
  applyTemplate: (
    doctorId: string,
    data: ApplyTemplateRequest
  ): Promise<{ message: string; count: number }> => {
    return request.post(`/consultation-fees/doctors/${doctorId}/apply-template`, data);
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
