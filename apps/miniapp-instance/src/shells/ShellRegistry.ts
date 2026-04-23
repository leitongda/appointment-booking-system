import { createShellLoader } from './ShellLoader';

/**
 * Shell 动态导入注册表
 * 按页面和变体组织，支持按需加载
 *
 * 使用方式：
 * const loader = shellLoaders.home['home-elderly'];
 * <ShellLoader loader={loader} />
 */

export const shellLoaders = {
  home: {
    // 首页 Shell
    standard: createShellLoader(() => import('./home/HomeStandard')),
    'home-elderly': createShellLoader(() => import('./home/HomeElderly')),
    'home-family': createShellLoader(() => import('./home/HomeFamily')),
    'home-premium': createShellLoader(() => import('./home/HomePremium')),
    'home-womens': createShellLoader(() => import('./home/HomeWomens')),
  },
  department: {
    // 科室列表 Shell
    sidebar: createShellLoader(() => import('./department/DeptSidebar')),
    'dept-large-grid': createShellLoader(() => import('./department/DeptLargeGrid')),
    minimal: createShellLoader(() => import('./department/DeptMinimal')),
    soft: createShellLoader(() => import('./department/DeptSoft')),
    colorful: createShellLoader(() => import('./department/DeptColorful')),
  },
  doctorList: {
    // 医生列表 Shell
    cards: createShellLoader(() => import('./doctor/DoctorCards')),
    'doctor-large-cards': createShellLoader(() => import('./doctor/DoctorLargeCards')),
    'doctor-cards-soft': createShellLoader(() => import('./doctor/DoctorCardsSoft')),
    'doctor-showcase': createShellLoader(() => import('./doctor/DoctorShowcase')),
  },
  doctorDetail: {
    // 医生详情 Shell
    standard: createShellLoader(() => import('./doctor/DoctorDetailStandard')),
    'doctor-detail-elderly': createShellLoader(() => import('./doctor/DoctorDetailElderly')),
    'doctor-detail-family': createShellLoader(() => import('./doctor/DoctorDetailFamily')),
    'doctor-detail-premium': createShellLoader(() => import('./doctor/DoctorDetailPremium')),
    'doctor-detail-womens': createShellLoader(() => import('./doctor/DoctorDetailWomens')),
  },
  appointment: {
    // 预约列表 Shell
    tabs: createShellLoader(() => import('./appointment/AppointTabs')),
    'appoint-simple': createShellLoader(() => import('./appointment/AppointSimple')),
  },
  profile: {
    // 个人中心 Shell
    standard: createShellLoader(() => import('./profile/ProfileStandard')),
    'profile-elderly': createShellLoader(() => import('./profile/ProfileElderly')),
    'profile-family': createShellLoader(() => import('./profile/ProfileFamily')),
    'profile-premium': createShellLoader(() => import('./profile/ProfilePremium')),
    'profile-womens': createShellLoader(() => import('./profile/ProfileWomens')),
  },
} as const;

export type ShellPageKey = keyof typeof shellLoaders;
export type ShellVariantId = string;

/**
 * 根据 Shell key 获取加载器
 */
export function getShellLoader(pageKey: ShellPageKey, variantId: ShellVariantId) {
  const pageLoaders = shellLoaders[pageKey];
  if (!pageLoaders) {
    console.warn(`[ShellRegistry] 未找到页面 ${pageKey} 的 Shell 加载器`);
    return null;
  }
  return pageLoaders[variantId] || null;
}

/**
 * 获取指定页面使用的所有 Shell 变体 ID
 * 用于构建时分析哪些 Shell 需要被打包
 */
export function getShellVariants(pageKey: ShellPageKey): string[] {
  const pageLoaders = shellLoaders[pageKey];
  if (!pageLoaders) return [];
  return Object.keys(pageLoaders);
}
