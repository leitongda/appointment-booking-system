import request from '../request';

// ========== 常见服务 ==========

export interface CommonServiceItem {
  id: string;
  name: string;
  code: string;
  icon?: string;
  variant?: string;
  linkType: number;
  linkUrl?: string;
  departmentId?: string;
  departmentName?: string;
  description?: string;
  sortOrder: number;
  status: number;
}

export interface CommonServiceListResponse {
  items: CommonServiceItem[];
}

// ========== 健康提醒 ==========

export interface HealthReminderConfig {
  id: string;
  reminderType: string;
  name: string;
  title?: string;
  content?: string;
  tips?: string[];
  recommendedInterval: number;
  sortOrder: number;
  status: number;
}

export interface UserHealthReminder {
  nextCheckDate?: string;
  lastCheckDate?: string;
  checkType?: string;
  tips?: string[];
  reminderContent?: string;
  hasData?: boolean;
}

// ========== API ==========

export const commonServiceApi = {
  /** 获取常见服务列表 */
  getCommonServices(params?: { storeId?: string; status?: number }) {
    return request.get<CommonServiceListResponse>('/content/common-services', { params });
  },

  /** 获取健康提醒配置（租户级静态） */
  getHealthReminderConfig(params?: { storeId?: string; reminderType?: string }) {
    return request.get<HealthReminderConfig[]>('/content/health-reminders/config', { params });
  },

  /** 获取当前用户的个性化健康提醒 */
  getMyHealthReminder(params?: { storeId?: string }) {
    return request.get<UserHealthReminder>('/content/health-reminders/my', { params });
  },
};
