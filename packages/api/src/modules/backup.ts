/**
 * 数据备份 API
 */
import request from '../request';

export interface BackupPrecheckResult {
  valid: boolean;
  tenant_id: string;
  tenant_name: string;
  record_counts: Record<string, number>;
  warnings: string[];
}

export interface BackupImportResult {
  success: boolean;
  imported_counts: Record<string, number>;
  errors: string[];
}

export const backupApi = {
  /** 导出租户数据备份（返回 Blob 用于文件下载） */
  exportData: (tenantId: string): Promise<Blob> => {
    // responseType: 'blob' 让 axios 返回二进制数据，但泛型推断不匹配，需 as any
    return request.post(`/backup/${tenantId}/export`, null, {
      responseType: 'blob',
    }) as any;
  },

  /** 导入前预检 */
  precheck: (tenantId: string, file: File): Promise<BackupPrecheckResult> => {
    const formData = new FormData();
    formData.append('file', file);
    return request.post(`/backup/${tenantId}/import/precheck`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  /** 导入数据恢复 */
  importData: (
    tenantId: string,
    file: File,
    overwrite: boolean = false,
  ): Promise<BackupImportResult> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('overwrite', String(overwrite));
    return request.post(`/backup/${tenantId}/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};
