import { request } from '../request';
import type { PageResult } from '@hospital/shared';

// ========== 用户（患者）列表项 ==========
export interface UserListItem {
  id: string;
  phone: string;
  nickname: string;
  avatar?: string;
  gender?: number;
  status: number;
  points: number;
  cardCount: number;
  appointmentCount: number;
  createdAt: string;
}

// ========== 就诊卡信息 ==========
export interface UserCard {
  id: string;
  cardNo?: string;
  name: string;
  phone: string;
  idCard?: string;
  gender?: number;
  age?: number;
  birthday?: string | null;
  relationship?: string;
  isDefault: boolean;
  source: number;
  appointmentCount: number;
  noShowCount: number;
  createdAt: string;
}

// ========== 用户（患者）详情 ==========
export interface UserDetail {
  id: string;
  phone: string;
  nickname: string;
  avatar?: string;
  gender?: number;
  openid?: string;
  status: number;
  points: number;
  createdAt: string;
  updatedAt?: string;
  // 统计信息
  cardCount: number;
  appointmentCount: number;
  noShowCount: number;
  // 就诊卡列表
  cards: UserCard[];
}

// ========== 查询参数 ==========
export interface UserListParams {
  keyword?: string;
  status?: number;
  storeId?: string;
  page?: number;
  pageSize?: number;
}

// ========== 用户更新数据 ==========
export interface UserUpdateData {
  nickname?: string;
  avatar?: string;
  gender?: number;
  phone?: string;
}

// ========== 就诊卡创建数据 ==========
export interface CardCreateData {
  name: string;
  phone: string;
  idCard?: string;
  gender?: number;
  birthday?: string;
  relationship?: string;
  isDefault?: boolean;
  province?: string;
  city?: string;
  district?: string;
  street?: string;
  idCardType?: number;
  ethnicity?: string;
  address?: string;
}

// ========== 就诊卡更新数据 ==========
export interface CardUpdateData {
  name?: string;
  phone?: string;
  idCard?: string;
  gender?: number;
  relationship?: string;
  isDefault?: boolean;
  province?: string;
  city?: string;
  district?: string;
  street?: string;
  idCardType?: number;
  ethnicity?: string;
  address?: string;
}

const PREFIX = '/user-manage';

export const userManageApi = {
  /**
   * 获取用户（患者）列表
   */
  getList: (params?: UserListParams): Promise<PageResult<UserListItem>> => {
    return request.get(PREFIX, { params });
  },

  /**
   * 获取用户（患者）详情
   */
  getDetail: (id: string): Promise<UserDetail> => {
    return request.get(`${PREFIX}/${id}`);
  },

  /**
   * 更新用户状态（禁用/启用）
   */
  updateStatus: (id: string, status: number): Promise<{ message: string }> => {
    return request.put(`${PREFIX}/${id}/status`, null, { params: { status } });
  },

  /**
   * 调整用户积分
   */
  adjustPoints: (id: string, amount: number, remark: string): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/${id}/points`, null, { params: { amount, remark } });
  },

  /**
   * 删除用户（患者）
   */
  deleteUser: (id: string): Promise<{ message: string }> => {
    return request.delete(`${PREFIX}/${id}`);
  },

  /**
   * 更新用户基本信息
   */
  updateUser: (id: string, data: UserUpdateData): Promise<UserDetail> => {
    return request.put(`${PREFIX}/${id}`, data);
  },

  /**
   * 为用户添加就诊卡
   */
  createCard: (userId: string, data: CardCreateData): Promise<UserCard> => {
    return request.post(`${PREFIX}/${userId}/cards`, data);
  },

  /**
   * 更新就诊卡信息
   */
  updateCard: (userId: string, cardId: string, data: CardUpdateData): Promise<UserCard> => {
    return request.put(`${PREFIX}/${userId}/cards/${cardId}`, data);
  },

  /**
   * 删除就诊卡
   */
  deleteCard: (userId: string, cardId: string): Promise<{ message: string }> => {
    return request.delete(`${PREFIX}/${userId}/cards/${cardId}`);
  },
};

