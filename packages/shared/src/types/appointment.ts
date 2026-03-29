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
  startTime?: string;
  endTime?: string;
  queueNumber?: number;
  fee?: number;
  status: number;
  signInTime?: string;
  callTime?: string;
  completeTime?: string;
  cancelTime?: string;
  cancelReason?: string;
  /** 病情描述/症状描述 */
  symptomDescription?: string;
  /** 门店名称（需后端补充） */
  storeName?: string;
  /** 签到方式（需后端补充） */
  checkInMethod?: string;
  createdAt: string;
  /** 是否为复诊 */
  isFollowUp?: boolean;
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
