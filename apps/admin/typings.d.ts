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
    setCenter(center: [number, number]): void;
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

// API 类型定义
declare namespace API {
  interface CurrentUser {
    id?: string;
    username?: string;
    name?: string;
    avatar?: string;
    phone?: string;
    roleId?: string;
    roleName?: string;
    roleCode?: string;
    permissions?: string[];
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
