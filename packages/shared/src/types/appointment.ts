export interface Appointment {
  id: string;
  appointmentNo: string;
  userId: string;
  patientId: string;
  patientName?: string;
  patientPhone?: string;
  doctorId: string;
  doctorName?: string;
  doctorTitle?: string;
  departmentId?: string;
  departmentName?: string;
  scheduleId: string;
  scheduleDate?: string;
  timeSlot?: string;
  queueNumber?: number;
  registrationFee?: number;
  fee?: number;
  status: number;
  signInTime?: string;
  callTime?: string;
  completeTime?: string;
  cancelTime?: string;
  cancelReason?: string;
  createdAt: string;
}

/** 预约详情（与 Appointment 相同，用于语义区分） */
export type AppointmentDetail = Appointment;

export interface AppointmentStatistics {
  total: number;
  pending: number;
  signedIn: number;
  inProgress: number;
  completed: number;
  cancelled: number;
  noShow: number;
}

export interface QueueInfo {
  currentNumber: number;
  waitingCount: number;
  currentPatient?: {
    id: string;
    name: string;
    queueNumber: number;
  };
  nextPatients: {
    id: string;
    name: string;
    queueNumber: number;
  }[];
}
