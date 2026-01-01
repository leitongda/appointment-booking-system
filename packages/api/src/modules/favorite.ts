import request from '../request';

export interface FavoriteTarget {
  id: string;
  name: string;
  title?: string;
  avatar?: string;
  departmentId?: string;
  departmentName?: string;
  specialty?: string;
  status?: number;
  description?: string;
  icon?: string;
}

export interface Favorite {
  id: string;
  userId: string;
  targetType: 'doctor' | 'department';
  targetId: string;
  createdAt: string;
  target?: FavoriteTarget;
}

export interface FavoriteListResult {
  data: Favorite[];
  total: number;
  page: number;
  pageSize: number;
}

export interface FavoriteCheckResult {
  isFavorited: boolean;
  favoriteId?: string;
}

export interface FavoriteCreateData {
  targetType: 'doctor' | 'department';
  targetId: string;
}

export const favoriteApi = {
  /**
   * 获取收藏列表
   */
  getList: (params?: { targetType?: 'doctor' | 'department'; page?: number; pageSize?: number }): Promise<FavoriteListResult> => {
    return request.get('/favorites', { params });
  },

  /**
   * 检查是否已收藏
   */
  check: (targetType: 'doctor' | 'department', targetId: string): Promise<FavoriteCheckResult> => {
    return request.get('/favorites/check', {
      params: { targetType, targetId },
    });
  },

  /**
   * 添加收藏
   */
  add: (data: FavoriteCreateData): Promise<Favorite> => {
    return request.post('/favorites', data);
  },

  /**
   * 取消收藏（通过收藏ID）
   */
  remove: (favoriteId: string): Promise<void> => {
    return request.delete(`/favorites/${favoriteId}`);
  },

  /**
   * 取消收藏（通过目标类型和ID）
   */
  removeByTarget: (targetType: 'doctor' | 'department', targetId: string): Promise<void> => {
    return request.delete(`/favorites/target/${targetType}/${targetId}`);
  },
};

