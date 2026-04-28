export interface Message {
  id: string;
  title: string;
  content?: string;
  message_type: string;
  is_read: number;
  created_at: string;
}
