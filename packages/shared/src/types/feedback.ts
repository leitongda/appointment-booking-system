export type FeedbackType = 'suggestion' | 'complaint' | 'bug' | 'other';
export type FeedbackStatus = 'pending' | 'processing' | 'resolved' | 'closed';

export interface Feedback {
  id: string;
  userId: string;
  userType: string;
  feedbackType: FeedbackType;
  title: string;
  content: string;
  images?: string[];
  contact?: string;
  status: FeedbackStatus;
  handlerId?: string;
  reply?: string;
  handledAt?: string;
  createdAt: string;
}
