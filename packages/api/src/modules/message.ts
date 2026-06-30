import request from '../request';
import type {
  Message,
  MessageType,
  UnreadCount,
  MessageTemplate,
  UnifiedTemplate,
  RecipientRule,
  PageResult,
} from '@hospital/shared';

export interface MessageListParams {
  userId?: string;
  userType?: string;
  messageType?: MessageType;
  isRead?: number;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

export interface UnifiedMessageListParams {
  messageType?: MessageType;
  isRead?: number;
  page?: number;
  pageSize?: number;
}

export interface UnifiedSendParams {
  tenantId: string;
  storeId?: string;
  recipientId: string;
  recipientType: string;
  recipientPhone?: string;
  recipientEmail?: string;
  recipientOpenid?: string;
  templateCode: string;
  variables?: Record<string, any>;
  messageType: MessageType;
  relatedId?: string;
  channels?: string[];
  priority?: number;
  title?: string;
  content?: string;
  extraData?: Record<string, any>;
}

export interface MessageCreateData {
  userId: string;
  userType: string;
  title: string;
  content?: string;
  messageType?: MessageType;
  relatedId?: string;
  extraData?: Record<string, any>;
}

export interface MessageBatchCreateData {
  userIds: string[];
  userType: string;
  title: string;
  content?: string;
  messageType?: MessageType;
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
  markAllAsRead: (userId: string, userType: string, messageType?: MessageType): Promise<void> => {
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
  getUnifiedTemplates: (params?: { messageType?: MessageType; status?: number; page?: number; pageSize?: number }): Promise<UnifiedTemplate[]> => {
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

  // ========== 统一消息端点 ==========

  // 获取消息列表（统一端点，基于 JWT 用户上下文）
  getUnifiedList: (params: UnifiedMessageListParams): Promise<PageResult<Message>> => {
    return request.get('/unified-messages/my', {
      params: {
        message_type: params.messageType,
        is_read: params.isRead,
        page: params.page,
        page_size: params.pageSize,
      }
    });
  },

  // 获取未读数（统一端点）
  getUnifiedUnreadCount: (): Promise<UnreadCount> => {
    return request.get('/unified-messages/unread-count');
  },

  // 标记已读（统一端点，自动从 JWT 提取用户信息）
  markAsReadUnified: (messageId: string): Promise<void> => {
    return request.post(`/unified-messages/read/${messageId}`);
  },

  // 全部标记已读（统一端点）
  markAllAsReadUnified: (messageType?: MessageType): Promise<void> => {
    return request.post('/unified-messages/read-all', null, {
      params: { message_type: messageType }
    });
  },

  // 发送消息（统一端点）
  sendUnified: (data: UnifiedSendParams): Promise<{ success: boolean; groupId?: string }> => {
    return request.post('/unified-messages/send', {
      tenant_id: data.tenantId,
      store_id: data.storeId,
      recipient_id: data.recipientId,
      recipient_type: data.recipientType,
      recipient_phone: data.recipientPhone,
      recipient_email: data.recipientEmail,
      recipient_openid: data.recipientOpenid,
      template_code: data.templateCode,
      variables: data.variables,
      message_type: data.messageType,
      related_id: data.relatedId,
      channels: data.channels,
      priority: data.priority,
      title: data.title,
      content: data.content,
      extra_data: data.extraData,
    });
  },

  // 批量发送（通过规则）
  sendBatchByRule: (ruleId: string, data: {
    messageType: MessageType;
    templateCode?: string;
    title?: string;
    content?: string;
    variables?: Record<string, any>;
    channels?: string[];
    priority?: number;
  }): Promise<{ message: string }> => {
    return request.post('/unified-messages/send-batch', data, { params: { rule_id: ruleId } });
  },

  // 删除消息（统一端点，自动从 JWT 提取用户信息）
  deleteUnified: (messageId: string): Promise<void> => {
    return request.delete(`/unified-messages/${messageId}`);
  },

  // 清空已读消息（统一端点，自动从 JWT 提取用户信息）
  clearReadUnified: (): Promise<void> => {
    return request.delete('/unified-messages/clear/read');
  },

  // 获取消息详情（统一端点，自动从 JWT 提取用户信息）
  getDetailUnified: (messageId: string): Promise<Message> => {
    return request.get(`/unified-messages/${messageId}`);
  },
};
