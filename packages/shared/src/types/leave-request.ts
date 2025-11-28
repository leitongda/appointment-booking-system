export type RequestType = 'stop_clinic' | 'schedule_change';
export type RequestStatus = 'pending' | 'approved' | 'rejected' | 'cancelled';
export type Period = 'morning' | 'afternoon' | 'evening' | 'all';

export interface LeaveRequest {
  id: string;
  doctorId: string;
  doctorName?: string;
  requestType: RequestType;
  scheduleId?: string;
  stopDate?: string;
  stopPeriod?: Period;
  originalDate?: string;
  originalPeriod?: Period;
  targetDate?: string;
  targetPeriod?: Period;
  reason: string;
  status: RequestStatus;
  reviewerId?: string;
  reviewComment?: string;
  reviewedAt?: string;
  affectedAppointments: number;
  createdAt: string;
}
