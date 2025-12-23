import { getBaseURL } from '../request';

const PREFIX = '/export';

export interface ExportAppointmentsParams {
  startDate?: string;
  endDate?: string;
  status?: number;
  doctorId?: string;
}

export interface ExportPatientsParams {
  keyword?: string;
}

export interface ExportSchedulesParams {
  startDate?: string;
  endDate?: string;
  doctorId?: string;
}

/**
 * 获取导出URL（用于下载）
 * 使用 getBaseURL() 获取当前配置的 API 基础路径
 */
const getExportUrl = (path: string, params?: Record<string, any>): string => {
  const baseUrl = getBaseURL();
  if (!baseUrl) {
    console.warn('[Export] API baseURL 未设置，请确保在应用初始化时调用 setBaseURL()');
  }
  const url = new URL(`${baseUrl}${PREFIX}${path}`, window.location.origin);
  
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.append(key, String(value));
      }
    });
  }
  
  return url.toString();
};

/**
 * 触发下载
 */
const triggerDownload = (url: string, filename?: string) => {
  const link = document.createElement('a');
  link.href = url;
  if (filename) {
    link.download = filename;
  }
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

export const exportApi = {
  /**
   * 导出预约记录
   */
  exportAppointments: (params?: ExportAppointmentsParams) => {
    const url = getExportUrl('/appointments', {
      start_date: params?.startDate,
      end_date: params?.endDate,
      status: params?.status,
      doctor_id: params?.doctorId,
    });
    triggerDownload(url, 'appointments.csv');
  },

  /**
   * 导出患者列表
   */
  exportPatients: (params?: ExportPatientsParams) => {
    const url = getExportUrl('/patients', params);
    triggerDownload(url, 'patients.csv');
  },

  /**
   * 导出排班记录
   */
  exportSchedules: (params?: ExportSchedulesParams) => {
    const url = getExportUrl('/schedules', {
      start_date: params?.startDate,
      end_date: params?.endDate,
      doctor_id: params?.doctorId,
    });
    triggerDownload(url, 'schedules.csv');
  },
};

