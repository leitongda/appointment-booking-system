export { authApi } from './modules/auth';
export { userApi } from './modules/user';
export { departmentApi } from './modules/department';
export { doctorApi } from './modules/doctor';
export { scheduleApi } from './modules/schedule';
export { appointmentApi } from './modules/appointment';
export { contentApi } from './modules/content';

export type { LoginParams, RegisterParams, TokenResult } from './modules/auth';
export type { PatientCreateData } from './modules/user';
export type { DepartmentListParams, DepartmentCreateData } from './modules/department';
export type { DoctorListParams, DoctorCreateData } from './modules/doctor';
export type { ScheduleListParams, ScheduleCreateData, ScheduleBatchCreateData, AvailableSchedule } from './modules/schedule';
export type { AppointmentListParams, AppointmentCreateData, AppointmentStatistics } from './modules/appointment';
