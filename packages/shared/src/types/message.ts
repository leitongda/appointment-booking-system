export type MessageType = 'appointment' | 'consultation' | 'schedule' | 'system' | 'stop_clinic' | 'feedback';

export interface Message {
  id: string;
  userId: string;
  userType: string;
  title: string;
  content?: string;
  messageType: MessageType;
  relatedId?: string;
  isRead: number;
  readAt?: string;
  createdAt: string;
}

export interface UnreadCount {
  total: number;
  appointment: number;
  consultation: number;
  schedule: number;
  system: number;
  stopClinic: number;
  feedback: number;
}

export interface MessageTemplate {
  id: string;
  code: string;
  name: string;
  messageType: MessageType;
  titleTemplate: string;
  contentTemplate: string;
  description?: string;
  status: number;
  createdAt: string;
  updatedAt: string;
}

export interface UnifiedTemplate {
  id: string;
  tenantId?: string;
  code?: string;
  name?: string;
  messageType?: string;
  eventType?: string;
  subjectTemplate?: string;
  htmlTemplate?: string;
  textTemplate?: string;
  wechatTemplateId?: string;
  variablesSchema?: Record<string, any>;
  status?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface RecipientRule {
  id: string;
  tenantId?: string;
  name?: string;
  eventType?: string;
  ruleType: 'role' | 'department' | 'user_list' | 'dynamic' | 'event_driven';
  ruleConfig: Record<string, any>;
  status?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface UsageStats {
  period?: Record<string, any>;
  total: number;
  byChannel: Record<string, number>;
  byType?: Record<string, number>;
  byStatus?: Record<string, number>;
  dailyTrend: Array<{ date: string; count: number }>;
}

export interface NotificationQuota {
  tenantId?: string;
  quotas: Record<string, number>;
  usage: Record<string, number>;
  remaining: Record<string, number>;
  usagePercent: Record<string, number>;
  periodStart?: string;
  periodEnd?: string;
}

export interface NotificationQuotaUpdate {
  smsMonthlyLimit?: number;
  emailMonthlyLimit?: number;
  wechatMonthlyLimit?: number;
  inAppMonthlyLimit?: number;
}
