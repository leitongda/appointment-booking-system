/**
 * 用户信息
 */
export interface User {
  id: string;
  phone: string;
  name: string;
  idCard?: string;
  gender: number;
  birthday?: string;
  avatar?: string;
  role: 'ADMIN' | 'DOCTOR' | 'PATIENT';
  status: number;
  createdAt: string;
  updatedAt: string;
}

/**
 * 登录请求
 */
export interface LoginParams {
  phone: string;
  password: string;
}

/**
 * 登录响应
 */
export interface LoginResult {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
  user: User;
}

/**
 * 就诊人信息
 */
export interface Patient {
  id: string;
  userId: string;
  name: string;
  phone: string;
  idCard?: string;
  gender: number;
  birthday?: string;
  relationship: string;
  isDefault: boolean;
  status: number;
  createdAt: string;
}

