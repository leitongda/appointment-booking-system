import { request } from '../request';
import type { PageResult } from '@hospital/shared';

// ========== 联系人类型 ==========
export type ContactType = 'patient' | 'doctor' | 'admin' | 'staff' | 'external';

// ========== 联系人状态 ==========
export type ContactStatus = 1 | 2; // 1=正常, 2=禁用

// ========== 联系人列表项 ==========
export interface ContactListItem {
  id: string;
  name: string;
  nickname?: string;
  avatar?: string;
  gender?: number;
  phone?: string;
  email?: string;
  contactType: ContactType;
  departmentId?: string;
  departmentName?: string;
  storeId?: string;
  storeName?: string;
  position?: string;
  organization?: string;
  status: ContactStatus;
  groups: ContactGroupItem[];
  tags: ContactTagItem[];
  remark?: string;
  createdAt: string;
  updatedAt?: string;
}

// ========== 联系人详情 ==========
export interface ContactDetail extends ContactListItem {
  channels: ContactChannel[];
}

// ========== 联系人渠道 ==========
export interface ContactChannel {
  id: string;
  channelType: string;
  channelValue: string;
  isPrimary: boolean;
  isVerified: boolean;
}

// ========== 联系人分组 ==========
export interface ContactGroup {
  id: string;
  name: string;
  parentId?: string;
  children?: ContactGroup[];
  contactCount?: number;
  sort?: number;
  createdAt?: string;
}

// ========== 联系人分组列表项（用于标签展示） ==========
export interface ContactGroupItem {
  id: string;
  name: string;
}

// ========== 联系人标签 ==========
export interface ContactTag {
  id: string;
  name: string;
  color?: string;
  contactCount?: number;
  createdAt?: string;
}

// ========== 联系人标签列表项（用于标签展示） ==========
export interface ContactTagItem {
  id: string;
  name: string;
  color?: string;
}

// ========== 查询参数 ==========
export interface ContactListParams {
  keyword?: string;
  contactType?: ContactType;
  groupId?: string;
  tagId?: string;
  status?: ContactStatus;
  page?: number;
  pageSize?: number;
}

// ========== 创建联系人 ==========
export interface ContactCreateData {
  name: string;
  nickname?: string;
  avatar?: string;
  gender?: number;
  phone?: string;
  email?: string;
  contactType: ContactType;
  departmentId?: string;
  storeId?: string;
  position?: string;
  organization?: string;
  groupIds?: string[];
  tagIds?: string[];
  remark?: string;
}

// ========== 更新联系人 ==========
export interface ContactUpdateData extends Partial<ContactCreateData> {}

// ========== 创建分组 ==========
export interface ContactGroupCreateData {
  name: string;
  parentId?: string;
  sort?: number;
}

// ========== 更新分组 ==========
export interface ContactGroupUpdateData {
  name?: string;
  parentId?: string;
  sort?: number;
}

// ========== 创建标签 ==========
export interface ContactTagCreateData {
  name: string;
  color?: string;
}

// ========== 更新标签 ==========
export interface ContactTagUpdateData {
  name?: string;
  color?: string;
}

// ========== 批量操作 ==========
export interface ContactBatchMoveData {
  contactIds: string[];
  groupId: string;
}

export interface ContactBatchTagData {
  contactIds: string[];
  tagIds: string[];
}

export interface ContactBatchDeleteData {
  contactIds: string[];
}

const PREFIX = '/contacts';

export const contactApi = {
  // ========== 联系人 CRUD ==========

  /**
   * 获取联系人列表
   */
  getList: (params?: ContactListParams): Promise<PageResult<ContactListItem>> => {
    return request.get(PREFIX, { params });
  },

  /**
   * 获取联系人详情
   */
  getDetail: (id: string): Promise<ContactDetail> => {
    return request.get(`${PREFIX}/${id}`);
  },

  /**
   * 创建联系人
   */
  create: (data: ContactCreateData): Promise<ContactDetail> => {
    return request.post(PREFIX, data);
  },

  /**
   * 更新联系人
   */
  update: (id: string, data: ContactUpdateData): Promise<ContactDetail> => {
    return request.put(`${PREFIX}/${id}`, data);
  },

  /**
   * 删除联系人
   */
  delete: (id: string): Promise<{ message: string }> => {
    return request.delete(`${PREFIX}/${id}`);
  },

  // ========== 批量操作 ==========

  /**
   * 批量删除联系人
   */
  batchDelete: (data: ContactBatchDeleteData): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/batch-delete`, data);
  },

  /**
   * 批量移动联系人到分组
   */
  batchMove: (data: ContactBatchMoveData): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/batch-move`, data);
  },

  /**
   * 批量打标签
   */
  batchTag: (data: ContactBatchTagData): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/batch-tag`, data);
  },

  // ========== 分组 ==========

  /**
   * 获取分组树
   */
  getGroupTree: (): Promise<ContactGroup[]> => {
    return request.get(`${PREFIX}/groups/tree`);
  },

  /**
   * 创建分组
   */
  createGroup: (data: ContactGroupCreateData): Promise<ContactGroup> => {
    return request.post(`${PREFIX}/groups`, data);
  },

  /**
   * 更新分组
   */
  updateGroup: (id: string, data: ContactGroupUpdateData): Promise<ContactGroup> => {
    return request.put(`${PREFIX}/groups/${id}`, data);
  },

  /**
   * 删除分组
   */
  deleteGroup: (id: string): Promise<{ message: string }> => {
    return request.delete(`${PREFIX}/groups/${id}`);
  },

  // ========== 标签 ==========

  /**
   * 获取标签列表
   */
  getTagList: (): Promise<ContactTag[]> => {
    return request.get(`${PREFIX}/tags`);
  },

  /**
   * 创建标签
   */
  createTag: (data: ContactTagCreateData): Promise<ContactTag> => {
    return request.post(`${PREFIX}/tags`, data);
  },

  /**
   * 更新标签
   */
  updateTag: (id: string, data: ContactTagUpdateData): Promise<ContactTag> => {
    return request.put(`${PREFIX}/tags/${id}`, data);
  },

  /**
   * 删除标签
   */
  deleteTag: (id: string): Promise<{ message: string }> => {
    return request.delete(`${PREFIX}/tags/${id}`);
  },
};
