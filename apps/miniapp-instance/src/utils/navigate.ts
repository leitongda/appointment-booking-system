import Taro from '@tarojs/taro';
import { getToken } from './auth';

/**
 * 统一导航工具函数
 * 提供导航栏 loading 动画、登录检查等功能
 */

// TabBar 页面路径列表
const TAB_BAR_PAGES = [
  '/pages/index/index',
  '/pages/appointment/index',
  '/pages/profile/index',
];

export interface NavigateOptions {
  /** 是否显示导航栏 loading */
  showLoading?: boolean;
  /** 是否检查登录状态（仅检查，不自动弹窗） */
  checkLogin?: boolean;
  /** 跳转方式：navigate（默认）、redirect、switchTab、reLaunch */
  type?: 'navigate' | 'redirect' | 'switchTab' | 'reLaunch';
}

/**
 * 判断是否为 TabBar 页面
 */
export const isTabBarPage = (url: string): boolean => {
  const path = url.split('?')[0];
  return TAB_BAR_PAGES.includes(path);
};

/**
 * 统一导航函数
 * @param url 目标页面路径
 * @param options 导航选项
 * @returns 是否成功跳转（登录检查失败时返回 false）
 */
export const navigateTo = async (
  url: string,
  options: NavigateOptions = {}
): Promise<boolean> => {
  const { showLoading = true, checkLogin = false, type } = options;

  // 登录检查
  if (checkLogin && !getToken()) {
    return false;
  }

  // 显示导航栏 loading
  if (showLoading) {
    Taro.showNavigationBarLoading();
  }

  try {
    // 自动判断跳转方式
    let navigateType = type;
    if (!navigateType) {
      navigateType = isTabBarPage(url) ? 'switchTab' : 'navigate';
    }

    switch (navigateType) {
      case 'switchTab':
        await Taro.switchTab({ url });
        break;
      case 'redirect':
        await Taro.redirectTo({ url });
        break;
      case 'reLaunch':
        await Taro.reLaunch({ url });
        break;
      case 'navigate':
      default:
        await Taro.navigateTo({ url });
        break;
    }
    return true;
  } catch (error) {
    console.error('[navigate] 跳转失败:', url, error);
    return false;
  } finally {
    if (showLoading) {
      Taro.hideNavigationBarLoading();
    }
  }
};

/**
 * 返回上一页
 * @param delta 返回的页面数，默认 1
 */
export const navigateBack = async (delta = 1): Promise<boolean> => {
  try {
    await Taro.navigateBack({ delta });
    return true;
  } catch (error) {
    console.error('[navigate] 返回失败:', error);
    // 如果返回失败（如页面栈只有一页），跳转到首页
    await Taro.switchTab({ url: '/pages/index/index' });
    return false;
  }
};

/**
 * 重定向到页面（替换当前页面）
 */
export const redirectTo = (url: string, options?: Omit<NavigateOptions, 'type'>) => {
  return navigateTo(url, { ...options, type: 'redirect' });
};

/**
 * 跳转到 TabBar 页面
 */
export const switchTab = (url: string, options?: Omit<NavigateOptions, 'type'>) => {
  return navigateTo(url, { ...options, type: 'switchTab' });
};
