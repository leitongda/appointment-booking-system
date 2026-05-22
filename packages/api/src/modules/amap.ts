import { request } from '../request';

export interface AmapPoi {
  name: string;
  address: string;
  location: string; // "lng,lat"
  pname: string;
  cityname: string;
  adname: string;
  type: string;
}

export interface AmapGeocode {
  formatted_address: string;
  province: string;
  city: string;
  district: string;
  street: string;
  number: string;
  location: string;
}

export interface AmapRegeoResult {
  formatted_address: string;
  addressComponent: {
    province: string;
    city: string;
    district: string;
    street: string;
    number: string;
  };
}

const PREFIX = '/amap';

export const amapApi = {
  /** 地理编码（地址→经纬度） */
  geocode: (address: string, city?: string): Promise<{ geocodes: AmapGeocode[] }> => {
    const params: Record<string, string> = { address };
    if (city) params.city = city;
    return request.get(`${PREFIX}/geocode`, { params });
  },

  /** 逆地理编码（经纬度→地址） */
  reverseGeocode: (location: string): Promise<AmapRegeoResult> => {
    return request.get(`${PREFIX}/regeo`, { params: { location } });
  },

  /** POI 搜索（关键词→地点列表） */
  searchPoi: (keywords: string, city?: string): Promise<{ pois: AmapPoi[]; count: number }> => {
    const params: Record<string, string> = { keywords };
    if (city) params.city = city;
    return request.get(`${PREFIX}/poi-search`, { params });
  },
};
