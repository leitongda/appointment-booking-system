import { userApi } from '@hospital/api';
import type { LoginResult, User } from '../types/user';
import type { WechatLoginResponse } from '@hospital/api';
import { setAuthSession } from '../miniapp-auth';

export type WechatLoginResolution =
  | { status: 'needs-profile'; openid: string }
  | { status: 'logged-in'; user: User | null };

const ensureAccessToken = (token?: string): string => {
  if (!token) {
    throw new Error('登录失败：Token 为空');
  }

  return token;
};

export const finalizeWechatUserBinding = async (
  result: LoginResult
): Promise<WechatLoginResolution> => {
  setAuthSession({
    accessToken: ensureAccessToken(result.accessToken),
    refreshToken: result.refreshToken,
    user: result.user,
  });

  return {
    status: 'logged-in',
    user: result.user ?? null,
  };
};

export const applyWechatLoginResult = async (
  result: WechatLoginResponse
): Promise<WechatLoginResolution> => {
  if (result.isNewUser || result.needBindPhone) {
    return {
      status: 'needs-profile',
      openid: result.openid,
    };
  }

  const profile = await userApi.getProfile().catch(() => null);

  setAuthSession({
    accessToken: ensureAccessToken(result.accessToken),
    refreshToken: result.refreshToken,
    user: profile,
  });

  return {
    status: 'logged-in',
    user: profile,
  };
};
