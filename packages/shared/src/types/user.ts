export interface User {
  id: string;
  phone: string;
  nickname?: string;
  avatar?: string;
  gender: number;
  status: number;
  createdAt?: string;
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
