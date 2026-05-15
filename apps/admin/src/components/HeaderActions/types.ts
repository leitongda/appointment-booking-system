export interface Message {
  id: string;
  title: string;
  content?: string;
  messageType: string;
  isRead: number;
  createdAt: string;
}
