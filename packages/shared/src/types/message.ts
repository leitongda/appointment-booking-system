export type MessageType = 'appointment' | 'consultation' | 'schedule' | 'system' | 'stop_clinic';

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
