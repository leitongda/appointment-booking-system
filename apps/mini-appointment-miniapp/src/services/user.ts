import { get, post, put, del } from '@/utils/request';
import type {
  User,
  Patient,
  Favorite,
  Banner,
  Notice,
  BookingRules,
  HospitalInfo,
  TimePeriodsConfig,
  Store,
  Feedback,
  PaginatedResponse
} from '@/types/api';

// ============ 用户/就诊人模块 ============

/**
 * 获取用户信息
 */
export function getUserProfile() {
  return get<User>('/users/profile');
}

/**
 * 更新用户信息
 */
export function updateUserProfile(data: Partial<User>) {
  return put<User>('/users/profile', data);
}

/**
 * 获取就诊人列表
 */
export function getPatients() {
  return get<Patient[]>('/users/patients');
}

/**
 * 获取就诊人详情
 */
export function getPatientById(id: string) {
  return get<Patient>(`/users/patients/${id}`);
}

/**
 * 添加就诊人
 */
export function createPatient(data: {
  name: string;
  phone: string;
  idCard?: string;
  gender?: number;
  birthday?: string;
  relationship?: string;
  isDefault?: boolean;
}) {
  return post<Patient>('/users/patients', data);
}

/**
 * 更新就诊人
 */
export function updatePatient(id: string, data: Partial<Patient>) {
  return put<Patient>(`/users/patients/${id}`, data);
}

/**
 * 删除就诊人
 */
export function deletePatient(id: string) {
  return del(`/users/patients/${id}`);
}

/**
 * 上传头像
 */
export function uploadAvatar(file: File) {
  return post<{ url: string }>('/users/avatar', { file });
}

// ============ 收藏模块 ============

/**
 * 检查是否已收藏
 */
export function checkFavorite(targetType: 'doctor' | 'department', targetId: string) {
  return get<{ isFavorited: boolean; favoriteId?: string }>('/favorites/check', {
    targetType,
    targetId
  });
}

/**
 * 添加收藏
 */
export function addFavorite(targetType: 'doctor' | 'department', targetId: string) {
  return post<Favorite>('/favorites', {
    targetType,
    targetId
  });
}

/**
 * 取消收藏（通过收藏ID）
 */
export function removeFavoriteById(favoriteId: string) {
  return del(`/favorites/${favoriteId}`);
}

/**
 * 取消收藏（通过目标）
 */
export function removeFavoriteByTarget(targetType: 'doctor' | 'department', targetId: string) {
  return del(`/favorites/target/${targetType}/${targetId}`);
}

/**
 * 获取收藏列表
 */
export function getFavorites(params?: {
  targetType?: 'doctor' | 'department';
  page?: number;
  pageSize?: number;
}) {
  return get<PaginatedResponse<Favorite>>('/favorites', params);
}

// ============ 内容模块 ============

/**
 * 获取活跃轮播图
 */
export function getActiveBanners(position?: string) {
  return get<Banner[]>('/content/banners/active', { position }, {
    needAuth: false
  });
}

/**
 * 获取已发布公告
 */
export function getPublishedNotices(limit?: number) {
  return get<Notice[]>('/content/notices/published', { limit }, {
    needAuth: false
  });
}

// ============ 设置模块 ============

/**
 * 获取预约规则（公开）
 */
export function getBookingRules(storeId?: string) {
  return get<BookingRules>('/settings/booking/rules', { storeId }, {
    needAuth: false
  });
}

/**
 * 获取医院信息
 */
export function getHospitalInfo() {
  return get<HospitalInfo>('/settings/hospital', {}, {
    needAuth: false
  });
}

/**
 * 获取时段配置
 */
export function getTimePeriods(storeId?: string) {
  return get<TimePeriodsConfig>('/settings/time-periods', { storeId }, {
    needAuth: false
  });
}

// ============ 门店模块 ============

/**
 * 通过编码获取门店信息（公开）
 */
export function getStoreByCode(code: string) {
  return get<Store>(`/stores/by-code/${code}`, {}, {
    needAuth: false
  });
}

/**
 * 获取门店签到二维码
 */
export function getStoreCheckinQRCode(storeId: string) {
  return get<{
    storeId: string;
    storeName: string;
    qrcodeContent: string;
    description: string;
  }>(`/stores/${storeId}/checkin-qrcode`);
}

// ============ 反馈模块 ============

/**
 * 提交反馈
 */
export function submitFeedback(data: {
  userId: string;
  userType?: string;
  feedbackType?: string;
  title: string;
  content: string;
  images?: string[];
  contact?: string;
}) {
  return post<Feedback>('/feedbacks', data);
}

/**
 * 获取我的反馈列表
 */
export function getMyFeedbacks(userId: string) {
  return get<Feedback[]>('/feedbacks/my', { user_id: userId });
}
