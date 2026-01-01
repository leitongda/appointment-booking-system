import request from '../request';
import type { StoreVisitTypeConfig, StoreVisitTypeConfigUpdate } from '@hospital/shared';

export interface StoreVisitTypeConfigResponse {
  data: StoreVisitTypeConfig;
  message?: string;
}

export const storeVisitTypeConfigApi = {
  /**
   * 获取门店复诊规则配置
   */
  getByStoreId: (storeId: string): Promise<StoreVisitTypeConfigResponse> => {
    return request.get(`/visit-type-configs/store/${storeId}`);
  },

  /**
   * 更新门店复诊规则配置（不存在则创建）
   */
  update: (storeId: string, data: StoreVisitTypeConfigUpdate): Promise<StoreVisitTypeConfigResponse> => {
    return request.put(`/visit-type-configs/store/${storeId}`, data);
  },

  /**
   * 删除门店复诊规则配置（恢复默认）
   */
  delete: (storeId: string): Promise<{ message: string }> => {
    return request.delete(`/visit-type-configs/store/${storeId}`);
  },
};

