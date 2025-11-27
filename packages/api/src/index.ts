// 导出请求实例
export { request, setBaseURL, setRequestInterceptor, setResponseInterceptor } from './request';

// 导出各模块 API
export * as authApi from './modules/auth';
export * as userApi from './modules/user';
export * as departmentApi from './modules/department';
export * as doctorApi from './modules/doctor';
export * as scheduleApi from './modules/schedule';
export * as appointmentApi from './modules/appointment';
export * as contentApi from './modules/content';

