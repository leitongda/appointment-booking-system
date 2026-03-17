import { useState, useCallback } from 'react';
import Taro from '@tarojs/taro';
import { wechatLogin, wechatPhoneLogin } from '@/services/auth';
import { checkLogin, clearAuth, setAuth } from '@/utils/auth';

/**
 * 登录 Hook
 */
export function useLogin() {
  const [loading, setLoading] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(checkLogin());

  // 微信登录
  const login = useCallback(async () => {
    try {
      setLoading(true);

      // 获取微信登录凭证
      const { code } = await Taro.login();

      // 调用后端登录接口
      const storeId = process.env.TARO_APP_STORE_ID || '';
      const result = await wechatLogin(code, storeId);

      if (result.needBindPhone) {
        // 需要绑定手机号
        return {
          success: false,
          needBindPhone: true,
          openid: result.openid
        };
      }

      // 登录成功，保存 Token
      if (result.accessToken) {
        setAuth({
          accessToken: result.accessToken,
          refreshToken: result.refreshToken
        });
        setIsLoggedIn(true);

        return {
          success: true,
          isNewUser: result.isNewUser
        };
      }

      return {
        success: false
      };
    } catch (error) {
      console.error('Login failed:', error);
      return {
        success: false,
        error
      };
    } finally {
      setLoading(false);
    }
  }, []);

  // 获取手机号并登录
  const loginWithPhone = useCallback(async (code: string, openid: string) => {
    try {
      setLoading(true);

      const storeId = process.env.TARO_APP_STORE_ID || '';
      const result = await wechatPhoneLogin(code, openid, storeId);

      // 保存 Token
      setAuth({
        accessToken: result.accessToken,
        refreshToken: result.refreshToken,
        user: result.user
      });
      setIsLoggedIn(true);

      return {
        success: true,
        user: result.user
      };
    } catch (error) {
      console.error('Login with phone failed:', error);
      return {
        success: false,
        error
      };
    } finally {
      setLoading(false);
    }
  }, []);

  // 退出登录
  const logout = useCallback(() => {
    clearAuth();
    setIsLoggedIn(false);
  }, []);

  return {
    loading,
    isLoggedIn,
    login,
    loginWithPhone,
    logout
  };
}
