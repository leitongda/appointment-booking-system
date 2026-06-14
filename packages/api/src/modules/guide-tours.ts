import { request } from '../request';

// ==================== 类型定义 ====================

/** 多语言文本 */
export interface LocaleMap {
  zh: string;
  en: string;
}

/** 指引步骤 */
export interface TourStep {
  target: string;
  placement: string;
  route: string;
  title: Record<string, string>;
  description: Record<string, string>;
  highlightPadding: number;
}

/** 用户端：指引项 */
export interface GuideTourItem {
  id: string;
  code: string;
  title: Record<string, string>;
  description?: Record<string, string>;
  steps: TourStep[];
  currentStep: number;
  progressStatus: number;
}

/** 用户端：进度 */
export interface GuideTourProgress {
  currentStep: number;
  status: number;
}

// ==================== API ====================

const PREFIX = '/guide-tours';

export const guideToursApi = {
  /** 获取当前用户可见的已发布指引列表（含进度） */
  getActive: (): Promise<GuideTourItem[]> => {
    return request.get(`${PREFIX}/active`);
  },

  /** 获取指定指引的用户进度 */
  getProgress: (tourId: string): Promise<GuideTourProgress> => {
    return request.get(`${PREFIX}/${tourId}/progress`);
  },

  /** 更新指引进度 */
  updateProgress: (tourId: string, data: { currentStep?: number; status?: number }): Promise<GuideTourProgress> => {
    return request.post(`${PREFIX}/${tourId}/progress`, data);
  },
};
