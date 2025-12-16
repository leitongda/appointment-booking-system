/**
 * 文件上传 API
 */
import { request } from '../request';

/** 上传结果 */
export interface UploadResult {
  url: string;
  key: string;
  size: number;
  content_type: string;
}

/** URL转存请求 */
export interface TransferRequest {
  url: string;
  folder?: string;
}

export const uploadApi = {
  /**
   * 上传图片
   * @param file 文件
   * @param folder 存储文件夹
   */
  upload: async (file: File, folder: string = 'images'): Promise<UploadResult> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('folder', folder);
    
    return request.post<UploadResult>('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  /**
   * 从URL转存图片
   * @param url 外部图片URL
   * @param folder 存储文件夹
   */
  transfer: async (url: string, folder: string = 'images'): Promise<UploadResult> => {
    return request.post<UploadResult>('/upload/transfer', { url, folder });
  },

  /**
   * 删除图片
   * @param key 存储键名
   */
  delete: async (key: string): Promise<{ message: string }> => {
    return request.delete(`/upload/${encodeURIComponent(key)}`);
  },
};

