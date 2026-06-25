import { request } from '../request';
import { createTTLCache } from '../utils/cache';

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

/**
 * 已发布指引列表的内存缓存。
 *
 * 该列表在多个全局位置被反复拉取(useGuidedTour、GuideTourButton、各端 layout),
 * 每次路由切换都会重新挂载并触发请求。这里加一层 60s TTL 缓存 + 并发去重,
 * 使全局在同一时间窗口内只发一次 /active 请求。
 */
const ACTIVE_TOUR_CACHE_KEY = 'active';
const activeToursCache = createTTLCache<GuideTourItem[]>({ ttl: 60_000 });

export const guideToursApi = {
  /** 获取当前用户可见的已发布指引列表（含进度） */
  getActive: (): Promise<GuideTourItem[]> => {
    return activeToursCache.getOrFetch(ACTIVE_TOUR_CACHE_KEY, () =>
      request.get(`${PREFIX}/active`),
    );
  },

  /** 获取指定指引的用户进度 */
  getProgress: (tourId: string): Promise<GuideTourProgress> => {
    return request.get(`${PREFIX}/${tourId}/progress`);
  },

  /** 更新指引进度 */
  updateProgress: (
    tourId: string,
    data: { currentStep?: number; status?: number },
  ): Promise<GuideTourProgress> => {
    return request
      .post(`${PREFIX}/${tourId}/progress`, data)
      .then((res) => {
        // 进度变更后失效列表缓存,保证下次拉取到最新进度
        activeToursCache.invalidate(ACTIVE_TOUR_CACHE_KEY);
        return res;
      });
  },
};
