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

/**
 * 应用微信登录结果。
 *
 * `getProfile` 采用依赖反转：shared 不能反向 import @hospital/api（会造成
 * shared → api 的循环依赖，目前仅靠 pnpm hoisting 偶然能跑）。故由调用方
 * （app 层，已持有 @hospital/api）注入 userApi.getProfile。与
 * components/ImageUpload 的 onUpload 注入范式一致。
 */
export const applyWechatLoginResult = async (
  result: WechatLoginResponse,
  getProfile?: () => Promise<unknown>,
): Promise<WechatLoginResolution> => {
  if (result.isNewUser || result.needBindPhone) {
    return {
      status: 'needs-profile',
      openid: result.openid,
    };
  }

  const profile = (getProfile
    ? await getProfile().catch(() => null)
    : null) as User | null;

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
