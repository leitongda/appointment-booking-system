import { request } from '../request';

export interface ExaminationReport {
  id: string;
  tenantId?: string;
  storeId?: string;
  recordId?: string;
  appointmentId: string;
  patientId: string;
  doctorId: string;
  reportType: string;
  title: string;
  description?: string;
  fileName: string;
  fileKey: string;
  fileSize: number;
  fileType: string;
  fileUrl?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface ExaminationReportListItem {
  id: string;
  reportType: string;
  title: string;
  fileName: string;
  fileSize: number;
  fileType: string;
  fileUrl?: string;
  createdAt?: string;
}

export interface ExaminationReportUploadParams {
  file: File;
  appointmentId: string;
  recordId?: string;
  reportType: string;
  title: string;
  description?: string;
}

export interface PageResult<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
}

const PREFIX = '/examination-reports';

export const examinationReportApi = {
  /**
   * 上传检查报告
   */
  upload: (params: ExaminationReportUploadParams): Promise<ExaminationReport> => {
    const formData = new FormData();
    formData.append('file', params.file);
    formData.append('appointment_id', params.appointmentId);
    if (params.recordId) formData.append('record_id', params.recordId);
    formData.append('report_type', params.reportType);
    formData.append('title', params.title);
    if (params.description) formData.append('description', params.description);

    return request.post(`${PREFIX}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  /**
   * 按预约获取报告列表
   */
  getByAppointment: (appointmentId: string): Promise<ExaminationReportListItem[]> => {
    return request.get(`${PREFIX}/appointment/${appointmentId}`);
  },

  /**
   * 按患者获取报告列表（分页）
   */
  getByPatient: (
    patientId: string,
    params?: { page?: number; pageSize?: number }
  ): Promise<PageResult<ExaminationReportListItem>> => {
    return request.get(`${PREFIX}/patient/${patientId}`, { params });
  },

  /**
   * 按病历获取报告列表
   */
  getByRecord: (recordId: string): Promise<ExaminationReportListItem[]> => {
    return request.get(`${PREFIX}/record/${recordId}`);
  },

  /**
   * 获取报告详情
   */
  getDetail: (id: string): Promise<ExaminationReport> => {
    return request.get(`${PREFIX}/${id}`);
  },

  /**
   * 删除报告
   */
  delete: (id: string): Promise<void> => {
    return request.delete(`${PREFIX}/${id}`);
  },

  // ---- 管理端接口 ----

  /**
   * 管理端：获取报告列表（分页，支持多条件筛选）
   */
  adminList: (params?: {
    keyword?: string;
    reportType?: string;
    storeId?: string;
    doctorId?: string;
    patientId?: string;
    startDate?: string;
    endDate?: string;
    page?: number;
    pageSize?: number;
  }): Promise<PageResult<ExaminationReportListItem>> => {
    const queryParams = params
      ? {
          keyword: params.keyword,
          report_type: params.reportType,
          store_id: params.storeId,
          doctor_id: params.doctorId,
          patient_id: params.patientId,
          start_date: params.startDate,
          end_date: params.endDate,
          page: params.page,
          page_size: params.pageSize,
        }
      : undefined;
    return request.get(PREFIX, { params: queryParams });
  },
};
