import request from '../request';

export interface NotificationPreference {
  id: string;
  appointmentEnabled: boolean;
  reminderEnabled: boolean;
  queueCallEnabled: boolean;
  stopClinicEnabled: boolean;
  systemEnabled: boolean;
  smsEnabled: boolean;
  emailEnabled: boolean;
  wechatEnabled: boolean;
  inAppEnabled: boolean;
  quietHoursStart?: string;
  quietHoursEnd?: string;
}

export const notificationPreferenceApi = {
  get: (): Promise<NotificationPreference> => {
    return request.get('/notification-preferences');
  },
  update: (data: Partial<NotificationPreference>): Promise<NotificationPreference> => {
    return request.put('/notification-preferences', data);
  },
};
