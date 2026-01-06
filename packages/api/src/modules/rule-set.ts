/**
 * 规则组管理 API
 */
import request from '../request';
import type {
  RuleSet,
  RuleWindow,
  RuleBookingPolicy,
  RuleCheckinPolicy,
  RuleCapacityPolicy,
  ShiftType,
  RulePreviewRequest,
  RulePreviewResponse,
  PageResult,
} from '@hospital/shared';

export interface RuleSetListParams {
  enabled?: boolean;
  shiftTypeId?: string;
  page?: number;
  pageSize?: number;
}

export interface RuleSetCreateData {
  name: string;
  enabled?: boolean;
  priority?: number;
  // 默认口径
  timeSource?: 'SERVER' | 'CLIENT';
  timezoneSource?: 'HOSPITAL' | 'SHIFT' | 'USER';
  comparePrecision?: 'SECOND' | 'MILLISECOND' | 'MINUTE';
  defaultOpenInclusive?: boolean;
  defaultCloseInclusive?: boolean;
  roundingMode?: 'NONE' | 'FLOOR_TO_MINUTE' | 'CEIL_TO_MINUTE';
  clockSkewToleranceSec?: number;
  description?: string;
  // 关联班次类型
  shiftTypeIds?: string[];
  // 时间窗
  windows?: Partial<RuleWindow>[];
  // 策略
  bookingPolicy?: Partial<RuleBookingPolicy>;
  checkinPolicy?: Partial<RuleCheckinPolicy>;
  capacityPolicy?: Partial<RuleCapacityPolicy>;
}

export interface RuleSetUpdateData {
  name?: string;
  enabled?: boolean;
  priority?: number;
  timeSource?: 'SERVER' | 'CLIENT';
  timezoneSource?: 'HOSPITAL' | 'SHIFT' | 'USER';
  comparePrecision?: 'SECOND' | 'MILLISECOND' | 'MINUTE';
  defaultOpenInclusive?: boolean;
  defaultCloseInclusive?: boolean;
  roundingMode?: 'NONE' | 'FLOOR_TO_MINUTE' | 'CEIL_TO_MINUTE';
  clockSkewToleranceSec?: number;
  description?: string;
  shiftTypeIds?: string[];
}

export interface RuleWindowCreateData {
  action: 'BOOK' | 'CHECKIN' | 'CANCEL' | 'HOLD_RELEASE';
  referencePoint: 'SHIFT_START' | 'SHIFT_END' | 'BOOKING_CREATED_AT';
  openOffsetSec: number;
  closeOffsetSec: number;
  openInclusive?: boolean;
  closeInclusive?: boolean;
  failPolicy?: 'REJECT' | 'ALLOW_WITH_TAG' | 'AUTO_TO_WAITLIST';
  failTag?: string;
  enabled?: boolean;
  description?: string;
}

export interface RuleWindowUpdateData {
  action?: 'BOOK' | 'CHECKIN' | 'CANCEL' | 'HOLD_RELEASE';
  referencePoint?: 'SHIFT_START' | 'SHIFT_END' | 'BOOKING_CREATED_AT';
  openOffsetSec?: number;
  closeOffsetSec?: number;
  openInclusive?: boolean;
  closeInclusive?: boolean;
  failPolicy?: 'REJECT' | 'ALLOW_WITH_TAG' | 'AUTO_TO_WAITLIST';
  failTag?: string;
  enabled?: boolean;
  description?: string;
}

/**
 * 规则组 API
 */
export const ruleSetApi = {
  /**
   * 获取规则组列表
   */
  async getList(params?: RuleSetListParams): Promise<PageResult<RuleSet>> {
    return request.get('/rule-sets', { params });
  },

  /**
   * 获取规则组详情
   */
  async getById(id: string): Promise<RuleSet> {
    return request.get(`/rule-sets/${id}`);
  },

  /**
   * 创建规则组
   */
  async create(data: RuleSetCreateData): Promise<RuleSet> {
    return request.post('/rule-sets', data);
  },

  /**
   * 更新规则组
   */
  async update(id: string, data: RuleSetUpdateData): Promise<RuleSet> {
    return request.put(`/rule-sets/${id}`, data);
  },

  /**
   * 删除规则组
   */
  async delete(id: string): Promise<void> {
    return request.delete(`/rule-sets/${id}`);
  },

  /**
   * 启用规则组
   */
  async enable(id: string): Promise<{ message: string }> {
    return request.post(`/rule-sets/${id}/enable`);
  },

  /**
   * 禁用规则组
   */
  async disable(id: string): Promise<{ message: string }> {
    return request.post(`/rule-sets/${id}/disable`);
  },

  /**
   * 预览规则效果
   */
  async preview(data: RulePreviewRequest): Promise<RulePreviewResponse> {
    return request.post('/rule-sets/preview', data);
  },

  // ==================== 时间窗管理 ====================

  /**
   * 创建时间窗
   */
  async createWindow(ruleSetId: string, data: RuleWindowCreateData): Promise<RuleWindow> {
    return request.post(`/rule-sets/${ruleSetId}/windows`, data);
  },

  /**
   * 更新时间窗
   */
  async updateWindow(windowId: string, data: RuleWindowUpdateData): Promise<RuleWindow> {
    return request.put(`/rule-sets/windows/${windowId}`, data);
  },

  /**
   * 删除时间窗
   */
  async deleteWindow(windowId: string): Promise<void> {
    return request.delete(`/rule-sets/windows/${windowId}`);
  },

  // ==================== 策略管理 ====================

  /**
   * 更新预约策略
   */
  async updateBookingPolicy(
    ruleSetId: string,
    data: Partial<RuleBookingPolicy>
  ): Promise<RuleBookingPolicy> {
    return request.put(`/rule-sets/${ruleSetId}/booking-policy`, data);
  },

  /**
   * 更新签到策略
   */
  async updateCheckinPolicy(
    ruleSetId: string,
    data: Partial<RuleCheckinPolicy>
  ): Promise<RuleCheckinPolicy> {
    return request.put(`/rule-sets/${ruleSetId}/checkin-policy`, data);
  },

  /**
   * 更新容量策略
   */
  async updateCapacityPolicy(
    ruleSetId: string,
    data: Partial<RuleCapacityPolicy>
  ): Promise<RuleCapacityPolicy> {
    return request.put(`/rule-sets/${ruleSetId}/capacity-policy`, data);
  },
};

/**
 * 班次类型 API
 */
export const shiftTypeApi = {
  /**
   * 获取班次类型列表（分页）
   */
  async getList(params?: {
    enabled?: boolean;
    keyword?: string;
    page?: number;
    pageSize?: number;
  }): Promise<PageResult<ShiftType>> {
    return request.get('/shift-types', { params });
  },

  /**
   * 获取所有班次类型
   */
  async getAll(): Promise<ShiftType[]> {
    return request.get('/shift-types/all');
  },

  /**
   * 获取启用的班次类型
   */
  async getEnabled(): Promise<ShiftType[]> {
    return request.get('/shift-types/all');
  },

  /**
   * 获取班次类型详情
   */
  async getById(id: string): Promise<ShiftType> {
    return request.get(`/shift-types/${id}`);
  },

  /**
   * 创建班次类型
   */
  async create(data: {
    code: string;
    name: string;
    description?: string;
    enabled?: boolean;
  }): Promise<ShiftType> {
    return request.post('/shift-types', data);
  },

  /**
   * 更新班次类型
   */
  async update(id: string, data: {
    name?: string;
    description?: string;
    enabled?: boolean;
  }): Promise<ShiftType> {
    return request.put(`/shift-types/${id}`, data);
  },

  /**
   * 删除班次类型
   */
  async delete(id: string): Promise<void> {
    return request.delete(`/shift-types/${id}`);
  },
};
