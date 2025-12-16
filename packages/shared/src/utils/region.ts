/**
 * 地区相关工具函数
 */

import type { RegionOption, RegionInfo, RegionValue, RegionCode } from '../types/region';

/**
 * 从级联选择器的值中提取地区名称
 * @param codes 地区编码数组 [省编码, 市编码, 区编码]
 * @param regionsData 地区数据
 * @returns 地区名称数组 [省名称, 市名称, 区名称]
 */
export function getRegionNames(
  codes: RegionCode,
  regionsData: RegionOption[]
): RegionValue {
  if (!codes || codes.length === 0) {
    return [];
  }

  const [provinceCode, cityCode, districtCode] = codes;
  const result: RegionValue = [];

  // 查找省份
  const province = regionsData.find((p) => p.value === provinceCode);
  if (province) {
    result.push(province.label);

    // 查找城市
    if (cityCode && province.children) {
      const city = province.children.find((c) => c.value === cityCode);
      if (city) {
        result.push(city.label);

        // 查找区县
        if (districtCode && city.children) {
          const district = city.children.find((d) => d.value === districtCode);
          if (district) {
            result.push(district.label);
          }
        }
      }
    }
  }

  return result;
}

/**
 * 从地区名称数组查找对应的编码
 * @param names 地区名称数组 [省名称, 市名称, 区名称]
 * @param regionsData 地区数据
 * @returns 地区编码数组 [省编码, 市编码, 区编码]
 */
export function getRegionCodes(
  names: RegionValue,
  regionsData: RegionOption[]
): RegionCode {
  if (!names || names.length === 0) {
    return [];
  }

  const [provinceName, cityName, districtName] = names;
  const result: RegionCode = [];

  // 查找省份编码
  const province = regionsData.find((p) => p.label === provinceName);
  if (province) {
    result.push(province.value);

    // 查找城市编码
    if (cityName && province.children) {
      const city = province.children.find((c) => c.label === cityName);
      if (city) {
        result.push(city.value);

        // 查找区县编码
        if (districtName && city.children) {
          const district = city.children.find((d) => d.label === districtName);
          if (district) {
            result.push(district.value);
          }
        }
      }
    }
  }

  return result;
}

/**
 * 将级联选择器的值转换为RegionInfo对象
 * @param value 级联选择器返回的值(名称数组)
 * @returns RegionInfo对象
 */
export function regionValueToInfo(value: RegionValue): RegionInfo {
  const [province, city, district] = value || [];
  return {
    province,
    city,
    district,
  };
}

/**
 * 将RegionInfo对象转换为级联选择器的值
 * @param info RegionInfo对象
 * @returns 地区名称数组
 */
export function regionInfoToValue(info: RegionInfo): RegionValue {
  return [info.province, info.city, info.district].filter(Boolean) as RegionValue;
}

/**
 * 格式化地区显示文本
 * @param info RegionInfo对象
 * @param separator 分隔符，默认为 "/"
 * @returns 格式化后的地区字符串，如 "贵州省/贵阳市/观山湖区"
 */
export function formatRegion(info: RegionInfo, separator: string = '/'): string {
  return [info.province, info.city, info.district]
    .filter(Boolean)
    .join(separator);
}

/**
 * 搜索地区（支持拼音和模糊搜索）
 * @param keyword 搜索关键词
 * @param regionsData 地区数据
 * @returns 匹配的地区路径数组
 */
export function searchRegion(
  keyword: string,
  regionsData: RegionOption[]
): RegionCode[] {
  if (!keyword) {
    return [];
  }

  const results: RegionCode[] = [];
  const lowerKeyword = keyword.toLowerCase();

  // 遍历省份
  for (const province of regionsData) {
    if (province.label.toLowerCase().includes(lowerKeyword)) {
      results.push([province.value]);
    }

    // 遍历城市
    if (province.children) {
      for (const city of province.children) {
        if (city.label.toLowerCase().includes(lowerKeyword)) {
          results.push([province.value, city.value]);
        }

        // 遍历区县
        if (city.children) {
          for (const district of city.children) {
            if (district.label.toLowerCase().includes(lowerKeyword)) {
              results.push([province.value, city.value, district.value]);
            }
          }
        }
      }
    }
  }

  return results;
}
