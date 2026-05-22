/**
 * 地图选点位置信息
 */
export interface LocationInfo {
  address: string;
  province: string;
  city: string;
  district: string;
  longitude: string;
  latitude: string;
}

/**
 * 拼接省市区+详细地址为完整地址字符串
 */
export function formatFullAddress(location: LocationInfo): string {
  return [location.province, location.city, location.district, location.address]
    .filter(Boolean)
    .join('');
}

/**
 * 将 LocationInfo 转为表单字段对象（6 个独立字段）
 */
export function locationToFields(location: LocationInfo): Record<string, string> {
  return {
    address: location.address,
    province: location.province,
    city: location.city,
    district: location.district,
    longitude: location.longitude,
    latitude: location.latitude,
  };
}

/**
 * 判断 LocationInfo 是否为空（无有效位置）
 */
export function isEmptyLocation(location?: LocationInfo): boolean {
  return !location?.address && !location?.longitude && !location?.latitude;
}
