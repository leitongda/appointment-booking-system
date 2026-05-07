export interface User {
  id: string;
  phone: string;
  nickname?: string;
  avatar?: string;
  gender: number;
  status: number;
  createdAt?: string;
  // 统一账号字段（兼容后端 AccountInfo.to_dict() 返回格式）
  roleType?: 'admin' | 'doctor' | 'user';
  permissions?: string[];
  // 用户额外信息（AccountInfo.to_dict() 扁平化后的字段）
  openid?: string;
  points?: number;
  isDoctor?: boolean;
  doctorId?: string;
}

export interface LoginParams {
  phone: string;
  password?: string;
  code?: string;
  type?: 'password' | 'code';
}

export interface LoginResult {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  user: User;
}

export interface Patient {
  id: string;
  userId: string;
  name: string;
  phone: string;
  idCard?: string;
  gender?: number;
  birthday?: string;
  relationship?: string;
  isDefault: boolean;
  province?: string;
  city?: string;
  district?: string;
  idCardType?: number;
  ethnicity?: string;
  address?: string;
}

export interface Admin {
  id: string;
  name: string;
  phone: string;
  avatar?: string;
  roleId: string;
  roleName?: string;
  status: number;
  lastLoginTime?: string;
  createdAt: string;
}
