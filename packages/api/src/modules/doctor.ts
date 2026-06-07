import request from '../request';
import type { Doctor, PageResult } from '@hospital/shared';
import { accountApi } from './account';

/**
 * 将 camelCase 字符串转换为 snake_case
 */
const toSnakeCase = (str: string): string => {
  return str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
};

/**
 * 将对象的所有键从 camelCase 转换为 snake_case
 */
const toSnakeCaseKeys = (obj: Record<string, any>): Record<string, any> => {
  const result: Record<string, any> = {};
  for (const key of Object.keys(obj)) {
    const snakeKey = toSnakeCase(key);
    result[snakeKey] = obj[key];
  }
  return result;
};

export interface DoctorListParams {
  name?: string;
  storeId?: string;
  departmentId?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

export interface DoctorRuleSetListParams {
  page?: number;
  pageSize?: number;
}

export interface DoctorCreateData {
  // 基础信息
  storeId?: string;
  departmentId: string;
  name: string;
  username?: string;
  phone?: string;
  gender?: number;
  avatar?: string;
  banner?: string;
  title?: string;
  yearsOfExperience?: number;
  
  // 资质信息
  education?: string;
  graduateSchool?: string;
  licenseNumber?: string;
  licenseImage?: string;
  honors?: string;
  
  // 坐诊设置
  scheduleDesc?: string;
  maxDailyAppointments?: number;
  onlineConsultEnabled?: number;
  onlineConsultFee?: number;
  
  // 展示设置
  pageStyle?: number;
  promoVideo?: string;
  tags?: string;
  specialty?: string;
  introduction?: string;
  
  // 其他设置
  isRecommended?: number;
  sortOrder?: number;
  status?: number;
  password?: string;
  
  // 诊费设置
  useFeeTemplate?: number;
}

export const doctorApi = {
  /**
   * 获取当前登录医生信息
   * 医生端专用，需要医生 token
   */
  getMe: (): Promise<Doctor> => {
    return request.get('/doctors/me');
  },

  /**
   * 获取医生端个人信息（doctor-portal 端点，含更多字段）
   */
  getMyProfile: (): Promise<Doctor> => {
    return request.get('/doctor-portal/me');
  },

  /**
   * 更新医生端个人信息
   */
  updateMyProfile: (data: {
    title?: string;
    specialty?: string;
    introduction?: string;
    avatar?: string;
    gender?: number;
    yearsOfExperience?: number;
    education?: string;
    graduateSchool?: string;
    licenseNumber?: string;
    honors?: string;
    scheduleDesc?: string;
  }): Promise<{ message: string; doctor: Doctor }> => {
    const requestData: Record<string, any> = {};
    if (data.title !== undefined) requestData.title = data.title;
    if (data.specialty !== undefined) requestData.specialty = data.specialty;
    if (data.introduction !== undefined) requestData.introduction = data.introduction;
    if (data.avatar !== undefined) requestData.avatar = data.avatar;
    if (data.gender !== undefined) requestData.gender = data.gender;
    if (data.yearsOfExperience !== undefined) requestData.years_of_experience = data.yearsOfExperience;
    if (data.education !== undefined) requestData.education = data.education;
    if (data.graduateSchool !== undefined) requestData.graduate_school = data.graduateSchool;
    if (data.licenseNumber !== undefined) requestData.license_number = data.licenseNumber;
    if (data.honors !== undefined) requestData.honors = data.honors;
    if (data.scheduleDesc !== undefined) requestData.schedule_desc = data.scheduleDesc;
    return request.put('/doctor-portal/me', requestData);
  },

  getList: (params?: DoctorListParams): Promise<PageResult<Doctor>> => {
    // 转换参数名为 snake_case
    const queryParams: Record<string, any> = {};
    if (params?.name) queryParams.name = params.name;
    if (params?.storeId && params.storeId !== 'all' && params.storeId !== '') {
      queryParams.store_id = params.storeId;
    }
    if (params?.departmentId) queryParams.department_id = params.departmentId;
    if (params?.status !== undefined && params?.status !== null) queryParams.status = params.status;
    if (params?.page) queryParams.page = params.page;
    if (params?.pageSize) queryParams.page_size = params.pageSize;
    return request.get('/doctors', { params: queryParams });
  },

  /**
   * 获取所有医生（管理端接口）
   * 用于管理后台需要获取完整医生列表的场景，如签到队列筛选
   */
  getAll: (): Promise<Doctor[]> => {
    return request.get('/doctors/all');
  },

  getRecommended: (limit?: number): Promise<Doctor[]> => {
    return request.get('/doctors/recommended', { params: { limit } });
  },

  getByDepartment: (departmentId: string): Promise<Doctor[]> => {
    return request.get(`/doctors/by-department/${departmentId}`);
  },

  /**
   * 检查医生账号是否已存在
   */
  checkUsername: (username: string, excludeId?: string): Promise<{ exists: boolean; suggestions: string[] }> => {
    return request.post('/doctors/check-username', { username, exclude_id: excludeId });
  },

  /**
   * 根据姓名生成医生账号
   */
  generateUsername: (name: string): Promise<{ username: string }> => {
    return request.post('/doctors/generate-username', { name });
  },

  /**
   * 搜索医生
   */
  search: async (keyword: string, limit?: number): Promise<Doctor[]> => {
    const result = await request.get<PageResult<Doctor>>('/doctors', {
      params: { name: keyword, page: 1, pageSize: limit || 10 },
    });
    return result.data ?? [];
  },

  getByStore: async (storeId: string): Promise<Doctor[]> => {
    const result = await request.get<any>('/doctors', {
      params: { store_id: storeId, page_size: 100 }
    });
    return result.data ?? [];
  },

  /**
   * 获取医生详情（公开接口，无需登录）
   * 用于患者端查看医生详情页
   */
  getDetail: (id: string): Promise<Doctor> => {
    return request.get(`/doctors/public/${id}`);
  },

  /**
   * 获取医生详情（管理端接口，需要管理员权限）
   */
  getDetailAdmin: (id: string): Promise<Doctor> => {
    return request.get(`/doctors/${id}`);
  },

  create: (data: DoctorCreateData): Promise<Doctor> => {
    // 自动将所有 camelCase 键转换为 snake_case
    const payload = toSnakeCaseKeys(data as Record<string, any>);
    return request.post('/doctors', payload);
  },

  update: (id: string, data: Partial<DoctorCreateData>): Promise<Doctor> => {
    // 自动将所有 camelCase 键转换为 snake_case，只保留有值的字段
    const payload: Record<string, any> = {};
    for (const [key, value] of Object.entries(data)) {
      if (value !== undefined) {
        payload[toSnakeCase(key)] = value;
      }
    }
    return request.put(`/doctors/${id}`, payload);
  },

  delete: (id: string): Promise<void> => {
    return request.delete(`/doctors/${id}`);
  },

  /**
   * 批量更新医生排序
   */
  batchUpdateSort: (items: { id: string; sortOrder: number }[]): Promise<{ message: string; count: number }> => {
    return request.put('/doctors/batch-sort', {
      items: items.map(item => ({ id: item.id, sort_order: item.sortOrder })),
    });
  },

  /**
   * 获取当前医生关联的预约规则组（只读）
   * 医生端专用，需要医生 token
   */
  getMyRuleSets: (params?: DoctorRuleSetListParams): Promise<any> => {
    return request.get('/doctor-portal/rule-sets', { params });
  },

  /**
   * 医生修改密码
   */
  changePassword: (data: { oldPassword: string; newPassword: string }): Promise<{ message: string }> => {
    return accountApi.changePassword(data);
  },

  /**
   * 医生刷新 Token
   */
  refreshToken: (refreshToken: string): Promise<{ accessToken?: string; refreshToken?: string; expiresIn?: number }> => {
    return request.post('/doctors/refresh', { refresh_token: refreshToken });
  },

  /**
   * 发送医生邮箱验证码
   */
  sendEmailCode: (email: string): Promise<{ message: string; code?: string }> => {
    return accountApi.sendEmailCode(email);
  },

  /**
   * 发送医生当前绑定邮箱验证码（解绑/换绑旧邮箱）
   */
  sendCurrentEmailCode: (): Promise<{ message: string; code?: string }> => {
    return accountApi.sendEmailCode();
  },

  /**
   * 绑定医生邮箱
   */
  emailBind: (data: { email: string; code: string }): Promise<{ message: string }> => {
    return accountApi.emailBind(data);
  },

  /**
   * 解绑医生邮箱
   */
  emailUnbind: (data: { code: string }): Promise<{ message: string }> => {
    return accountApi.emailUnbind(data);
  },

  /**
   * 更换医生邮箱
   */
  emailChange: (data: { newEmail: string; newEmailCode: string; oldEmailCode: string }): Promise<{ message: string }> => {
    return accountApi.emailChange(data);
  },

  /**
   * 创建医生评价
   */
  createReview: (data: {
    appointmentId: string;
    doctorId: string;
    patientId?: string;
    rating: number;
    content?: string;
    tags?: string[];
    isAnonymous?: boolean;
  }): Promise<any> => {
    const payload: Record<string, any> = {
      appointment_id: data.appointmentId,
      doctor_id: data.doctorId,
      rating: data.rating,
    };
    if (data.patientId) payload.patient_id = data.patientId;
    if (data.content) payload.content = data.content;
    if (data.tags) payload.tags = data.tags;
    if (data.isAnonymous !== undefined) payload.is_anonymous = data.isAnonymous;
    return request.post('/doctor-reviews', payload);
  },

  /**
   * 获取医生评价列表（公开）
   */
  getDoctorReviews: (doctorId: string, params?: { page?: number; pageSize?: number }): Promise<any> => {
    return request.get(`/doctor-reviews/doctors/${doctorId}`, {
      params: { page: params?.page, page_size: params?.pageSize },
    });
  },

  /**
   * 回复评价（管理端）
   */
  replyReview: (reviewId: string, reply: string): Promise<any> => {
    return request.post(`/doctor-reviews/${reviewId}/reply`, { reply });
  },
};
