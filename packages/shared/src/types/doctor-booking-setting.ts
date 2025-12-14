export interface DoctorBookingSetting {
  id: string;
  storeId: string;
  storeName?: string;
  doctorId: string;
  doctorName?: string;
  bookingStartOffset: number;  // 预约开始偏移天数，0表示当天
  bookingRangeDays: number;    // 预约范围天数，1-90天
  releaseTime: string;         // 放号时间 HH:mm格式
  status: number;              // 状态: 0禁用 1启用
  createdAt: string;
  updatedAt: string;
}

export interface DoctorBookingSettingCreate {
  storeId: string;
  doctorId: string;
  bookingStartOffset?: number;
  bookingRangeDays?: number;
  releaseTime?: string;
  status?: number;
}

export interface DoctorBookingSettingUpdate {
  bookingStartOffset?: number;
  bookingRangeDays?: number;
  releaseTime?: string;
  status?: number;
}
