/**
 * 地区数据类型定义
 */

/**
 * 地区选项接口 - 用于级联选择器
 */
export interface RegionOption {
  /** 地区编码 (如: "110000") */
  value: string;
  /** 地区名称 (如: "北京市") */
  label: string;
  /** 子地区列表 */
  children?: RegionOption[];
}

/**
 * 地区信息接口 - 用于表单数据
 */
export interface RegionInfo {
  /** 省份 */
  province?: string;
  /** 城市 */
  city?: string;
  /** 区县 */
  district?: string;
}

/**
 * 地区值类型 - 级联选择器返回的值
 * 格式: [省份, 城市, 区县]
 */
export type RegionValue = [string?, string?, string?];

/**
 * 地区编码类型 - 级联选择器返回的编码
 * 格式: [省编码, 市编码, 区编码]
 */
export type RegionCode = [string?, string?, string?];
