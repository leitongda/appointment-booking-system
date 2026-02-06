import { request } from '../request';

/** 事件类型选项（从后端获取） */
export interface EventTypeOption {
  value: string;
  label: string;
}

/** 门店邮件接收人 */
export interface StoreEmailRecipient {
  id: string;
  storeId: string;
  storeName?: string;
  name: string;
  email: string;
  eventTypes: string[];
  status: number;
  createdAt: string;
  updatedAt: string;
}

/** 列表查询参数 */
export interface StoreEmailRecipientListParams {
  storeId?: string;
  keyword?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

/** 创建参数 */
export interface StoreEmailRecipientCreateData {
  storeId: string;
  name: string;
  email: string;
  eventTypes: string[];
  status?: number;
}

/** 更新参数 */
export interface StoreEmailRecipientUpdateData {
  name?: string;
  email?: string;
  eventTypes?: string[];
  status?: number;
}

const PREFIX = '/store-email-recipients';

export const storeEmailRecipientApi = {
  /** 获取可用事件类型列表 */
  getEventTypes: (): Promise<EventTypeOption[]> => {
    return request.get(`${PREFIX}/event-types`);
  },

  /** 获取门店邮件接收人列表 */
  getList: (params?: StoreEmailRecipientListParams): Promise<{
    data: StoreEmailRecipient[];
    total: number;
    page: number;
    pageSize: number;
  }> => {
    return request.get(PREFIX, {
      params: {
        store_id: params?.storeId,
        keyword: params?.keyword,
        status: params?.status,
        page: params?.page || 1,
        page_size: params?.pageSize || 10,
      },
    });
  },

  /** 获取门店邮件接收人详情 */
  getById: (id: string): Promise<StoreEmailRecipient> => {
    return request.get(`${PREFIX}/${id}`);
  },

  /** 创建门店邮件接收人 */
  create: (data: StoreEmailRecipientCreateData): Promise<StoreEmailRecipient> => {
    return request.post(PREFIX, {
      store_id: data.storeId,
      name: data.name,
      email: data.email,
      event_types: data.eventTypes,
      status: data.status ?? 1,
    });
  },

  /** 更新门店邮件接收人 */
  update: (id: string, data: StoreEmailRecipientUpdateData): Promise<StoreEmailRecipient> => {
    const payload: Record<string, unknown> = {};
    if (data.name !== undefined) payload.name = data.name;
    if (data.email !== undefined) payload.email = data.email;
    if (data.eventTypes !== undefined) payload.event_types = data.eventTypes;
    if (data.status !== undefined) payload.status = data.status;
    return request.put(`${PREFIX}/${id}`, payload);
  },

  /** 删除门店邮件接收人 */
  delete: (id: string): Promise<{ message: string }> => {
    return request.delete(`${PREFIX}/${id}`);
  },
};
