export { authApi } from './modules/auth';
export { userApi } from './modules/user';
export { departmentApi } from './modules/department';
export { doctorApi } from './modules/doctor';
export { scheduleApi } from './modules/schedule';
export { appointmentApi } from './modules/appointment';
export { medicalRecordApi } from './modules/medical-record';
export { contentApi } from './modules/content';
export { statisticsApi } from './modules/statistics';
export { adminApi } from './modules/admin';
export { settingsApi } from './modules/settings';
export { patientApi } from './modules/patient';
export { exportApi } from './modules/export';
export { storeApi } from './modules/store';
export { messageApi } from './modules/message';

export type { LoginParams, RegisterParams, TokenResult } from './modules/auth';
export type { PatientCreateData } from './modules/user';
export type { DepartmentListParams, DepartmentCreateData } from './modules/department';
export type { DoctorListParams, DoctorCreateData } from './modules/doctor';
export type { ScheduleListParams, ScheduleCreateData, ScheduleBatchCreateData, AvailableSchedule } from './modules/schedule';
export type { AppointmentListParams, AppointmentCreateData, AppointmentStatistics } from './modules/appointment';
export type {
  MedicalRecord,
  MedicalRecordListItem,
  MedicalRecordListParams,
  MedicalRecordCreateData,
  MedicalRecordUpdateData,
} from './modules/medical-record';
export type {
  OverviewData,
  TrendItem,
  RevenueTrendItem,
  StatusStatItem,
  DepartmentRankingItem,
  DoctorRankingItem,
  TimeSlotItem,
  WeekdayItem,
} from './modules/statistics';
