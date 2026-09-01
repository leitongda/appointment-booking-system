/**
 * 动态 Shell 加载器
 * 根据模板的 pageShells 配置动态导入对应的 Shell 组件
 * 实现 tree-shaking：未绑定的 Shell 不会被打包
 */

import { lazy, ComponentType } from 'react';
import { resolveShellModule } from './ShellLoader';

// 页面路径类型（与模板 pageShells 键名对应）
type PagePath = 'home' | 'department' | 'doctorList' | 'doctorDetail' | 'appointment' | 'profile';

// Shell 变体 ID 类型
type VariantId = string;

// Lazy 组件类型
type LazyShellComponent = ComponentType<any>;

/**
 * Shell 映射表：页面 -> 变体ID -> 动态导入函数
 * 使用显式映射而非动态路径，确保 Webpack 可静态分析
 */
const SHELL_IMPORT_MAP: Record<PagePath, Record<VariantId, () => Promise<Record<string, unknown>>>> = {
  home: {
    standard: () => import('./home/HomeStandard'),
    'home-elderly': () => import('./home/HomeElderly'),
    'home-premium': () => import('./home/HomePremium'),
    'home-family': () => import('./home/HomeFamily'),
    'home-womens': () => import('./home/HomeWomens'),
  },
  department: {
    sidebar: () => import('./department/DeptSidebar'),
    'dept-large-grid': () => import('./department/DeptLargeGrid'),
    'dept-minimal': () => import('./department/DeptMinimal'),
    'dept-colorful': () => import('./department/DeptColorful'),
    'dept-soft': () => import('./department/DeptSoft'),
  },
  doctorList: {
    cards: () => import('./doctor/DoctorCards'),
    'doctor-large-cards': () => import('./doctor/DoctorLargeCards'),
    'doctor-showcase': () => import('./doctor/DoctorShowcase'),
    'doctor-cards-soft': () => import('./doctor/DoctorCardsSoft'),
  },
  doctorDetail: {
    standard: () => import('./doctor/DoctorDetailStandard'),
    'doctor-detail-elderly': () => import('./doctor/DoctorDetailElderly'),
    'doctor-detail-family': () => import('./doctor/DoctorDetailFamily'),
    'doctor-detail-premium': () => import('./doctor/DoctorDetailPremium'),
    'doctor-detail-womens': () => import('./doctor/DoctorDetailWomens'),
  },
  appointment: {
    tabs: () => import('./appointment/AppointTabs'),
    'appoint-simple': () => import('./appointment/AppointSimple'),
  },
  profile: {
    standard: () => import('./profile/ProfileStandard'),
    'profile-elderly': () => import('./profile/ProfileElderly'),
    'profile-family': () => import('./profile/ProfileFamily'),
    'profile-premium': () => import('./profile/ProfilePremium'),
    'profile-womens': () => import('./profile/ProfileWomens'),
  },
};

/**
 * 缓存已加载的 Shell（避免重复懒加载创建）
 */
const shellCache = new Map<string, LazyShellComponent>();

/**
 * 获取指定页面和变体的 Shell 组件
 * @param pagePath 页面路径（home, department 等）
 * @param variantId Shell 变体 ID
 * @param useLazy 是否使用懒加载（默认 true）
 * @returns Shell 组件
 */
export function loadShell(
  pagePath: PagePath,
  variantId: string,
  useLazy: boolean = true
): LazyShellComponent | null {
  const cacheKey = `${pagePath}:${variantId}`;

  // 检查缓存
  if (shellCache.has(cacheKey)) {
    return shellCache.get(cacheKey)!;
  }

  const pageMap = SHELL_IMPORT_MAP[pagePath];
  if (!pageMap) {
    console.warn(`[loadShells] 未知的页面路径: ${pagePath}`);
    return null;
  }

  const importFn = pageMap[variantId] || pageMap['standard'];
  if (!importFn) {
    console.warn(`[loadShells] 页面 ${pagePath} 没有找到变体 ${variantId}，也无 standard 回退`);
    return null;
  }

  if (useLazy) {
    // 使用 React.lazy 包装动态导入
    const LazyComponent = lazy(() => importFn().then((module) => ({ default: resolveShellModule(module) })));
    shellCache.set(cacheKey, LazyComponent);
    return LazyComponent;
  } else {
    // 同步加载（用于首屏优化）
    // 这个分支目前不使用，保留用于未来可能的 SSR 场景
    return null;
  }
}

/**
 * 批量加载模板绑定的所有 Shell
 * @param pageShells 模板的 pageShells 配置
 * @returns 页面路径到 Shell 组件的映射
 */
export function loadTemplateShells(
  pageShells: Partial<Record<PagePath, string>>
): Partial<Record<PagePath, LazyShellComponent>> {
  const result: Partial<Record<PagePath, LazyShellComponent>> = {};

  for (const [pagePath, variantId] of Object.entries(pageShells)) {
    const shell = loadShell(pagePath as PagePath, variantId);
    if (shell) {
      result[pagePath as PagePath] = shell;
    }
  }

  return result;
}

/**
 * 清除 Shell 缓存（主要用于测试或动态切换模板场景）
 */
export function clearShellCache(): void {
  shellCache.clear();
}
