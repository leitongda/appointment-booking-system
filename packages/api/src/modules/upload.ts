/**
 * 文件上传 API
 */
import { request } from '../request';

/** 缩略图信息 */
export interface ThumbnailInfo {
  url: string;
  key: string;
  width: number;
  height: number;
  size: number;
}

/** 上传结果 */
export interface UploadResult {
  url: string;
  key: string;
  size: number;
  content_type: string;
  thumbnails?: Record<string, ThumbnailInfo>;
}

/** URL转存请求 */
export interface TransferRequest {
  url: string;
  folder?: string;
}

/** 上传选项 */
export interface UploadOptions {
  folder?: string;
  generateThumbnails?: boolean;
}

export const uploadApi = {
  /**
   * 上传图片
   * @param file 文件
   * @param options 上传选项
   */
  upload: async (file: File, options: UploadOptions | string = 'images'): Promise<UploadResult> => {
    const formData = new FormData();
    formData.append('file', file);
    
    // 兼容旧的字符串参数
    if (typeof options === 'string') {
      formData.append('folder', options);
    } else {
      formData.append('folder', options.folder || 'images');
      if (options.generateThumbnails) {
        formData.append('generate_thumbnails', 'true');
      }
    }
    
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

