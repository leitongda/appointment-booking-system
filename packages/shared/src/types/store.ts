export interface Store {
  id: string;
  name: string;
  code?: string;
  address?: string;
  province?: string;
  city?: string;
  district?: string;
  latitude?: string;
  longitude?: string;
  phone?: string;
  contactPerson?: string;
  description?: string;
  openingTime?: string;
  closingTime?: string;
  workingDays?: string;
  image?: string;
  logo?: string;
  password?: string;
  email?: string;
  themeStyle?: string;
  sortOrder: number;
  status: number;
  departmentCount?: number;
  createdAt: string;
  updatedAt: string;
  // 微信配置（敏感字段不返回或掩码处理）
  wechatAppId?: string;
  wechatMchId?: string;
  wechatNotifyUrl?: string;
}

/**
 * 门店微信配置
 */
export interface StoreWechatConfig {
  appId?: string;
  appSecret?: string;
  mchId?: string;
  apiKey?: string;
  notifyUrl?: string;
}

export interface StoreDepartment {
  id: string;
  storeId: string;
  departmentId: string;
  departmentName?: string;
  floor?: string;
  room?: string;
  status: number;
  createdAt: string;
}

/**
 * 门店上下文 - 用于患者端多门店隔离
 */
export interface StoreContext {
  /** 门店ID */
  storeId: string;
  /** 门店编码 */
  storeCode: string;
  /** 门店名称 */
  storeName: string;
  /** 门店logo */
  storeLogo?: string;
  /** 门店主题风格 */
  storeTheme?: string;
  /** 门店电话 */
  storePhone?: string;
  /** 门店地址 */
  storeAddress?: string;
}

/**
 * 门店上下文存储键名
 */
export const STORE_CONTEXT_KEY = 'hospital_store_context';

/**
 * 从 Store 对象创建 StoreContext
 */
export function createStoreContext(store: Store): StoreContext {
  return {
    storeId: store.id,
    storeCode: store.code || '',
    storeName: store.name,
    storeLogo: store.logo,
    storeTheme: store.themeStyle,
    storePhone: store.phone,
    storeAddress: store.address,
  };
}
