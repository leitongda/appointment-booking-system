/**
 * 数据导入导出 API
 */
import { request } from '../request';

const BASE_URL = '/api/v1/data';

export interface ImportResult {
  success_count: number;
  fail_count: number;
  total: number;
  errors: Array<{
    row: number;
    data: Record<string, any>;
    errors: string[];
  }>;
}

export const dataApi = {
  // ==================== 导出接口 ====================
  
  /** 获取预约导出 URL (使用原有导出接口) */
  getExportAppointmentsUrl: (params?: { startDate?: string; endDate?: string; status?: number; doctorId?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.startDate) searchParams.append('start_date', params.startDate);
    if (params?.endDate) searchParams.append('end_date', params.endDate);
    if (params?.status !== undefined) searchParams.append('status', String(params.status));
    if (params?.doctorId) searchParams.append('doctor_id', params.doctorId);
    const query = searchParams.toString();
    return `/api/v1/export/appointments${query ? `?${query}` : ''}`;
  },
  
  /** 获取医生导出 URL */
  getExportDoctorsUrl: (params?: { storeId?: string; departmentId?: string; status?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.storeId) searchParams.append('store_id', params.storeId);
    if (params?.departmentId) searchParams.append('department_id', params.departmentId);
    if (params?.status !== undefined) searchParams.append('status', String(params.status));
    const query = searchParams.toString();
    return `${BASE_URL}/export/doctors${query ? `?${query}` : ''}`;
  },

  /** 获取患者导出 URL */
  getExportPatientsUrl: (keyword?: string) => {
    const query = keyword ? `?keyword=${encodeURIComponent(keyword)}` : '';
    return `${BASE_URL}/export/patients${query}`;
  },

  /** 获取科室导出 URL */
  getExportDepartmentsUrl: (params?: { storeId?: string; status?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.storeId) searchParams.append('store_id', params.storeId);
    if (params?.status !== undefined) searchParams.append('status', String(params.status));
    const query = searchParams.toString();
    return `${BASE_URL}/export/departments${query ? `?${query}` : ''}`;
  },

  /** 获取门店导出 URL */
  getExportStoresUrl: (status?: number) => {
    const query = status !== undefined ? `?status=${status}` : '';
    return `${BASE_URL}/export/stores${query}`;
  },

  /** 获取排班模板导出 URL */
  getExportScheduleTemplatesUrl: (params?: { storeId?: string; doctorId?: string; status?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.storeId) searchParams.append('store_id', params.storeId);
    if (params?.doctorId) searchParams.append('doctor_id', params.doctorId);
    if (params?.status !== undefined) searchParams.append('status', String(params.status));
    const query = searchParams.toString();
    return `${BASE_URL}/export/schedule-templates${query ? `?${query}` : ''}`;
  },

  /** 获取系统用户导出 URL */
  getExportUsersUrl: (params?: { storeId?: string; status?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.storeId) searchParams.append('store_id', params.storeId);
    if (params?.status !== undefined) searchParams.append('status', String(params.status));
    const query = searchParams.toString();
    return `${BASE_URL}/export/users${query ? `?${query}` : ''}`;
  },

  /** 获取操作日志导出 URL */
  getExportLogsUrl: (params?: { module?: string; result?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.module) searchParams.append('module', params.module);
    if (params?.result) searchParams.append('log_result', params.result);
    const query = searchParams.toString();
    return `${BASE_URL}/export/logs${query ? `?${query}` : ''}`;
  },

  /** 获取用户反馈导出 URL */
  getExportFeedbacksUrl: (params?: { status?: string; feedbackType?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.append('status', params.status);
    if (params?.feedbackType) searchParams.append('feedback_type', params.feedbackType);
    const query = searchParams.toString();
    return `${BASE_URL}/export/feedbacks${query ? `?${query}` : ''}`;
  },

  // ==================== 模板下载 ====================
  
  /** 获取医生导入模板 URL */
  getDoctorTemplateUrl: () => `${BASE_URL}/template/doctors`,
  
  /** 获取患者导入模板 URL */
  getPatientTemplateUrl: () => `${BASE_URL}/template/patients`,
  
  /** 获取科室导入模板 URL */
  getDepartmentTemplateUrl: () => `${BASE_URL}/template/departments`,
  
  /** 获取门店导入模板 URL */
  getStoreTemplateUrl: () => `${BASE_URL}/template/stores`,

  // ==================== 导入接口 ====================
  
  /** 获取医生导入 URL */
  getImportDoctorsUrl: () => `${BASE_URL}/import/doctors`,
  
  /** 获取患者导入 URL */
  getImportPatientsUrl: () => `${BASE_URL}/import/patients`,
  
  /** 获取科室导入 URL */
  getImportDepartmentsUrl: () => `${BASE_URL}/import/departments`,
  
  /** 获取门店导入 URL */
  getImportStoresUrl: () => `${BASE_URL}/import/stores`,
};

export default dataApi;
