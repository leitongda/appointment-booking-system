import request from '../request';
import type { Message, UnreadCount, MessageTemplate, UnifiedTemplate, RecipientRule, PageResult } from '@hospital/shared';

export interface MessageListParams {
  userId?: string;
  userType?: string;
  messageType?: string;
  isRead?: number;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

export interface MessageCreateData {
  userId: string;
  userType: string;
  title: string;
  content?: string;
  messageType?: string;
  relatedId?: string;
  extraData?: Record<string, any>;
}

export interface MessageBatchCreateData {
  userIds: string[];
  userType: string;
  title: string;
  content?: string;
  messageType?: string;
  relatedId?: string;
}

export const messageApi = {
  // 获取消息列表（用户端）
  getList: (params: MessageListParams): Promise<PageResult<Message>> => {
    return request.get('/messages/my', {
      params: {
        user_id: params.userId,
        user_type: params.userType,
        message_type: params.messageType,
        is_read: params.isRead,
        page: params.page,
        page_size: params.pageSize,
      }
    });
  },

  // 获取所有消息列表（管理端）
  getAllList: (params: MessageListParams): Promise<PageResult<Message>> => {
    return request.get('/messages', {
      params: {
        user_id: params.userId,
        user_type: params.userType,
        message_type: params.messageType,
        is_read: params.isRead,
        keyword: params.keyword,
        page: params.page,
        page_size: params.pageSize,
      }
    });
  },

  // 获取未读数量
  getUnreadCount: (userId: string, userType: string): Promise<UnreadCount> => {
    return request.get('/messages/unread-count', {
      params: { user_id: userId, user_type: userType }
    });
  },

  // 获取消息详情
  getDetail: (id: string): Promise<Message> => {
    return request.get(`/messages/${id}`);
  },

  // 标记为已读
  markAsRead: (messageId: string, userId: string): Promise<void> => {
    return request.post(`/messages/read/${messageId}`, null, {
      params: { user_id: userId }
    });
  },

  // 标记全部已读
  markAllAsRead: (userId: string, userType: string, messageType?: string): Promise<void> => {
    return request.post('/messages/read-all', null, {
      params: { user_id: userId, user_type: userType, message_type: messageType }
    });
  },

  // 删除消息
  delete: (messageId: string, userId: string): Promise<void> => {
    return request.delete(`/messages/${messageId}`, {
      params: { user_id: userId }
    });
  },

  // 清空已读消息
  clearRead: (userId: string, userType: string): Promise<void> => {
    return request.delete('/messages/clear/read', {
      params: { user_id: userId, user_type: userType }
    });
  },

  // 发送消息（管理端）
  send: (data: MessageCreateData): Promise<Message> => {
    return request.post('/messages/send', data);
  },

  // 批量发送消息（管理端）
  sendBatch: (data: MessageBatchCreateData): Promise<{ message: string }> => {
    return request.post('/messages/send-batch', data);
  },

  // 获取消息模板列表
  getTemplates: (params?: { status?: number; page?: number; pageSize?: number }): Promise<PageResult<MessageTemplate>> => {
    return request.get('/messages/templates', {
      params: {
        status: params?.status,
        page: params?.page,
        page_size: params?.pageSize,
      }
    });
  },

  // 创建消息模板
  createTemplate: (data: Partial<MessageTemplate>): Promise<MessageTemplate> => {
    return request.post('/messages/templates', data);
  },

  // 更新消息模板
  updateTemplate: (id: string, data: Partial<MessageTemplate>): Promise<MessageTemplate> => {
    return request.put(`/messages/templates/${id}`, data);
  },

  // 删除消息模板
  deleteTemplate: (id: string): Promise<void> => {
    return request.delete(`/messages/templates/${id}`);
  },

  // 统一模板 API
  getUnifiedTemplates: (params?: { messageType?: string; status?: number; page?: number; pageSize?: number }): Promise<UnifiedTemplate[]> => {
    return request.get('/unified-messages/templates', {
      params: {
        message_type: params?.messageType,
        status: params?.status,
        page: params?.page,
        page_size: params?.pageSize,
      },
    });
  },

  createUnifiedTemplate: (data: Partial<UnifiedTemplate>): Promise<UnifiedTemplate> => {
    return request.post('/unified-messages/templates', data);
  },

  updateUnifiedTemplate: (id: string, data: Partial<UnifiedTemplate>): Promise<UnifiedTemplate> => {
    return request.put(`/unified-messages/templates/${id}`, data);
  },

  deleteUnifiedTemplate: (id: string): Promise<void> => {
    return request.delete(`/unified-messages/templates/${id}`);
  },

  // 收件人规则 API
  getRecipientRules: (params?: { eventType?: string }): Promise<RecipientRule[]> => {
    return request.get('/unified-messages/rules', { params });
  },

  createRecipientRule: (data: Partial<RecipientRule>): Promise<RecipientRule> => {
    return request.post('/unified-messages/rules', data);
  },

  updateRecipientRule: (id: string, data: Partial<RecipientRule>): Promise<RecipientRule> => {
    return request.put(`/unified-messages/rules/${id}`, data);
  },

  deleteRecipientRule: (id: string): Promise<void> => {
    return request.delete(`/unified-messages/rules/${id}`);
  },

  // 批量发送（通过规则）
  sendBatchByRule: (ruleId: string, data: {
    messageType: string;
    templateCode?: string;
    title?: string;
    content?: string;
    variables?: Record<string, any>;
    channels?: string[];
    priority?: number;
  }): Promise<{ message: string }> => {
    return request.post('/unified-messages/send-batch', data, { params: { rule_id: ruleId } });
  },
};
