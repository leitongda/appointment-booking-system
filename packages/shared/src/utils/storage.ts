/**
 * 本地存储 Key
 */
export const STORAGE_KEYS = {
  TOKEN: 'hospital_token',
  REFRESH_TOKEN: 'hospital_refresh_token',
  USER_INFO: 'hospital_user_info',
  /** 上次访问的页面路径 */
  LAST_PATH: 'hospital_last_path',
  /** 切换租户/门店后需要恢复的页面路径 */
  SWITCH_REDIRECT_PATH: 'hospital_switch_redirect',
  /** 登录方式 */
  LOGIN_TYPE: 'hospital_login_type',
  /** 手机号登录子方式 */
  PHONE_LOGIN_TYPE: 'hospital_phone_login_type',
  /** 门店上下文 */
  STORE_CONTEXT: 'hospital_store_context',
  /** 当前租户 ID（用于多租户切换） */
  CURRENT_TENANT_ID: 'hospital_current_tenant_id',
  /** 当前门店（用于多门店切换） */
  CURRENT_STORE: 'hospital_current_store',
  /** 租户暂停/禁用标记 */
  TENANT_SUSPENDED: 'hospital_tenant_suspended',
  /** 当前主题 */
  CURRENT_THEME: 'hospital_current_theme',
  /** 字体模式 (standard | elder) */
  FONT_MODE: 'hospital_font_mode',
  /** 菜单展开状态 */
  MENU_OPEN_KEYS: 'hospital_menu_open_keys',
} as const;

/**
 * 获取存储
 */
export const getStorage = <T = string>(key: string): T | null => {
  try {
    const value = localStorage.getItem(key);
    if (!value) return null;
    return JSON.parse(value) as T;
  } catch {
    return localStorage.getItem(key) as T | null;
  }
};

/**
 * 设置存储
 */
export const setStorage = (key: string, value: any): void => {
  if (typeof value === 'string') {
    localStorage.setItem(key, value);
  } else {
    localStorage.setItem(key, JSON.stringify(value));
  }
};

/**
 * 移除存储
 */
export const removeStorage = (key: string): void => {
  localStorage.removeItem(key);
};

/**
 * 清空存储
 */
export const clearStorage = (): void => {
  localStorage.clear();
};

/**
 * Token 相关
 */
export const getToken = (): string | null => {
  return getStorage<string>(STORAGE_KEYS.TOKEN);
};

export const setToken = (token: string): void => {
  setStorage(STORAGE_KEYS.TOKEN, token);
};

export const removeToken = (): void => {
  removeStorage(STORAGE_KEYS.TOKEN);
  removeStorage(STORAGE_KEYS.REFRESH_TOKEN);
};

/**
 * Token 失效处理工具
 * 用于防止多个请求同时返回 401 时重复弹窗
 */
let isTokenExpiredHandling = false;
let tokenExpiredTimer: ReturnType<typeof setTimeout> | null = null;

/**
 * 处理 Token 失效
 * @param callback 回调函数，用于执行实际的处理逻辑（如弹窗、跳转）
 * @returns 如果是第一次触发返回 true，重复触发返回 false
 */
export const handleTokenExpired = (callback?: () => void): boolean => {
  // 如果正在处理中，忽略后续请求
  if (isTokenExpiredHandling) {
    return false;
  }
  
  isTokenExpiredHandling = true;
  
  // 清除 token
  removeToken();
  
  // 执行回调
  callback?.();
  
  // 清除之前的定时器
  if (tokenExpiredTimer) {
    clearTimeout(tokenExpiredTimer);
  }
  
  // 3 秒后重置状态，允许再次触发
  tokenExpiredTimer = setTimeout(() => {
    isTokenExpiredHandling = false;
    tokenExpiredTimer = null;
  }, 3000);
  
  return true;
};

/**
 * 重置 Token 失效处理状态
 * 在登录成功后调用
 */
export const resetTokenExpiredState = (): void => {
  isTokenExpiredHandling = false;
  isAuthExpired = false;
  if (tokenExpiredTimer) {
    clearTimeout(tokenExpiredTimer);
    tokenExpiredTimer = null;
  }
};

// ─── 全局"认证已失效"门控 ──────────────────────────────────

/**
 * 全局认证失效标记。
 * 一旦设为 true，所有通过 @hospital/api 发出的请求都会被短路，
 * 避免定时器/轮询/组件重渲染持续发出无效请求导致 "(1/3) 无限重复"。
 *
 * - 在 401 响应拦截器中通过 markAuthExpired() 设置
 * - 在登录成功后通过 resetTokenExpiredState() 清除
 */
let isAuthExpired = false;

/**
 * 从 JWT token 中解析过期时间戳（秒），解析失败返回 null
 */
export const parseJwtExp = (token: string): number | null => {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    return typeof payload.exp === 'number' ? payload.exp : null;
  } catch {
    return null;
  }
};

/**
 * 检查当前 token 是否已过期（纯客户端 exp 判断，无网络请求）
 * - 无 token → false（不触发，由其他逻辑处理）
 * - 解析失败 → false（保守策略，不误杀）
 * - exp < now → true
 */
export const isTokenExpired = (): boolean => {
  const token = getToken();
  if (!token) return false;
  const exp = parseJwtExp(token);
  if (exp === null) return false;
  return Date.now() >= exp * 1000;
};

/** 标记认证已失效（401 拦截器调用） */
export const markAuthExpired = (): void => {
  isAuthExpired = true;
};

/** 检查认证是否已失效（请求拦截器调用） */
export const checkAuthExpired = (): boolean => {
  return isAuthExpired;
};

