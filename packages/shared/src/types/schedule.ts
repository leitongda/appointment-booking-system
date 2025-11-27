export interface Schedule {
  id: string;
  doctorId: string;
  doctorName?: string;
  departmentName?: string;
  scheduleDate: string;
  timeSlot: string;
  startTime?: string;
  endTime?: string;
  totalSlots: number;
  bookedSlots: number;
  status: number;
  createdAt: string;
}

export interface AvailableSchedule {
  id: string;
  scheduleDate: string;
  timeSlot: string;
  availableSlots: number;
  startTime?: string;
  endTime?: string;
}
