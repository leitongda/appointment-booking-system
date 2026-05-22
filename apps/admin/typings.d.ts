declare module 'slash2';
declare module '*.css';
declare module '*.less';
declare module '*.scss';
declare module '*.sass';
declare module '*.svg';
declare module '*.png';
declare module '*.jpg';
declare module '*.jpeg';
declare module '*.gif';
declare module '*.bmp';
declare module '*.tiff';

// 高德地图类型声明
declare namespace AMap {
  class Map {
    constructor(container: string | HTMLElement, opts?: MapOptions);
    destroy(): void;
    setCenter(center: [number, number] | LngLat): void;
    setZoom(zoom: number): void;
    on(event: string, handler: (e: any) => void): void;
    add(overlay: any): void;
    remove(overlay: any): void;
    getCenter(): LngLat;
  }

  interface MapOptions {
    zoom?: number;
    center?: [number, number];
    viewMode?: '2D' | '3D';
    resizeEnable?: boolean;
  }

  class LngLat {
    constructor(lng: number, lat: number);
    getLng(): number;
    getLat(): number;
  }

  class Marker {
    constructor(opts?: MarkerOptions);
    setPosition(position: [number, number] | LngLat): void;
    getPosition(): LngLat;
    setMap(map: Map | null): void;
    on(event: string, handler: (e: any) => void): void;
  }

  interface MarkerOptions {
    position?: [number, number] | LngLat;
    draggable?: boolean;
    animation?: string;
  }

  class Geocoder {
    constructor(opts?: GeocoderOptions);
    getAddress(
      location: [number, number] | LngLat,
      callback: (status: string, result: GeocoderResult) => void
    ): void;
  }

  interface GeocoderOptions {
    city?: string;
    radius?: number;
    extensions?: 'base' | 'all';
  }

  interface GeocoderResult {
    info: string;
    regeocode?: {
      formattedAddress: string;
      addressComponent: {
        province: string;
        city: string;
        district: string;
        street: string;
        streetNumber: string;
        township: string;
        neighborhood: { name: string };
        building: { name: string };
      };
    };
  }

  class PlaceSearch {
    constructor(opts?: PlaceSearchOptions);
    search(
      keyword: string,
      callback: (status: string, result: PlaceSearchResult) => void
    ): void;
  }

  interface PlaceSearchOptions {
    city?: string;
    citylimit?: boolean;
    pageSize?: number;
    pageIndex?: number;
    extensions?: 'base' | 'all';
  }

  interface PlaceSearchResult {
    info: string;
    poiList?: {
      pois: POI[];
      count: number;
    };
  }

  interface POI {
    id: string;
    name: string;
    address: string;
    location: LngLat;
    tel?: string;
    type?: string;
    pname?: string;
    cityname?: string;
    adname?: string;
  }

  class AutoComplete {
    constructor(opts?: AutoCompleteOptions);
    search(
      keyword: string,
      callback: (status: string, result: AutoCompleteResult) => void
    ): void;
  }

  interface AutoCompleteOptions {
    city?: string;
    citylimit?: boolean;
    datatype?: string;
  }

  interface AutoCompleteResult {
    info: string;
    tips?: AutoCompleteTip[];
  }

  interface AutoCompleteTip {
    id: string;
    name: string;
    district: string;
    address: string;
    location?: LngLat;
  }
}

declare const AMap: typeof AMap;

// 门店信息类型
interface StoreInfo {
  id: string;
  name: string;
  logo?: string;
  themeStyle?: string;
}

// UmiJS 类型声明（修复类型检查问题）
declare module '@umijs/max' {
  export function defineConfig(config: any): any;
  export const history: any;
  export function useModel(namespace: string): any;
  export function useAccess(): any;
  export function useLocation(): any;
  export function useParams(): any;
  export function useSearchParams(): any;
  export function useRequest<TData, TParams extends any[]>(
    service: any,
    options?: any
  ): any;
  export const request: any;
  export type RequestConfig = any;
  export type RunTimeLayoutConfig = any;
  export const Outlet: any;
}

// umi 模块声明（兼容旧导入路径）
declare module 'umi' {
  export * from '@umijs/max';
}

// axios 模块声明（pnpm 严格模式下可能找不到类型）
declare module 'axios' {
  export interface AxiosRequestConfig {
    url?: string;
    method?: string;
    baseURL?: string;
    headers?: Record<string, any>;
    params?: any;
    data?: any;
    timeout?: number;
    [key: string]: any;
  }
  export interface AxiosResponse<T = any> {
    data: T;
    status: number;
    statusText: string;
    headers: Record<string, any>;
    config: AxiosRequestConfig;
  }
  export interface InternalAxiosRequestConfig extends AxiosRequestConfig {
    headers: Record<string, any>;
  }
  export interface AxiosInstance {
    (config: AxiosRequestConfig): Promise<any>;
    get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>;
    post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>;
    put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>;
    delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>;
    patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>;
    interceptors: {
      request: { use: (...args: any[]) => any };
      response: { use: (...args: any[]) => any };
    };
    defaults: AxiosRequestConfig;
  }
  export interface AxiosStatic extends AxiosInstance {
    create(config?: AxiosRequestConfig): AxiosInstance;
  }
  declare const axios: AxiosStatic;
  export default axios;
}

// API 类型定义
declare namespace API {
  interface CurrentUser {
    id?: string;
    username?: string;
    name?: string;
    avatar?: string;
    phone?: string;
    // 统一账号字段（后端 AccountInfo.to_dict() 返回）
    roleType?: 'admin' | 'doctor' | 'user';
    tenantId?: string;
    email?: string;
    // 角色信息
    roleId?: string;
    roleName?: string;
    roleCode?: string;
    // 当前选中门店
    currentStoreId?: string;
    currentStoreName?: string;
    // 兼容旧字段
    storeId?: string;
    storeName?: string;
    // 绑定的所有门店
    storeIds?: string[];
    stores?: StoreInfo[];
    // 权限相关
    permissions?: string[];
    isSuperAdmin?: boolean;
    isStoreAdmin?: boolean;
    isTenantAdmin?: boolean;
    isPlatformAdmin?: boolean;
    canSwitchStores?: boolean;
    // 租户状态（多租户支持）
    tenant?: {
      id?: string;
      name?: string;
      tenantCode?: string;
      status?: number;
      subscriptionPlanName?: string;
      subscriptionEndAt?: string;
      isSubscriptionActive?: boolean;
    };
    // 其他字段
    status?: number;
    lastLoginAt?: string;
    lastLoginIp?: string;
    createdAt?: string;
  }

  interface LoginParams {
    username: string;
    password: string;
  }

  interface LoginResult {
    accessToken: string;
    refreshToken: string;
  }

  interface PageParams {
    current?: number;
    pageSize?: number;
  }

  interface PageResult<T> {
    data: T[];
    total: number;
    success: boolean;
  }
}
