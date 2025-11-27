export interface Appointment {
  id: string;
  appointmentNo: string;
  userId: string;
  patientId: string;
  patientName?: string;
  patientPhone?: string;
  doctorId: string;
  doctorName?: string;
  departmentName?: string;
  scheduleId: string;
  scheduleDate?: string;
  timeSlot?: string;
  queueNumber?: number;
  registrationFee?: number;
  status: number;
  signInTime?: string;
  callTime?: string;
  completeTime?: string;
  cancelTime?: string;
  cancelReason?: string;
  createdAt: string;
}

export interface AppointmentStatistics {
  total: number;
  pending: number;
  signedIn: number;
  inProgress: number;
  completed: number;
  cancelled: number;
  noShow: number;
}
