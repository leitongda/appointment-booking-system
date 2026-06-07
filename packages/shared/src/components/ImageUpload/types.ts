/**
 * 图片上传组件类型定义
 */

/** 剪裁比例预设 */
export type AspectRatioPreset = '1:1' | '16:9' | '4:3' | '3:2' | 'free';

/** 剪裁比例映射 */
export const ASPECT_RATIO_MAP: Record<AspectRatioPreset, number | undefined> = {
  '1:1': 1,
  '16:9': 16 / 9,
  '4:3': 4 / 3,
  '3:2': 3 / 2,
  'free': undefined,
};

/** 输出图片格式 */
export type ImageOutputFormat = 'jpeg' | 'png' | 'webp';

/** 预设尺寸选项 */
export interface PresetSize {
  label: string;
  width: number;
  height: number;
}

/** 水印位置 */
export type WatermarkPosition = 'topLeft' | 'topRight' | 'bottomLeft' | 'bottomRight' | 'center';

/** 水印配置 */
export interface WatermarkConfig {
  /** 水印文字 */
  text: string;
  /** 字体大小，默认 16 */
  fontSize?: number;
  /** 文字颜色，默认 rgba(255,255,255,0.5) */
  color?: string;
  /** 透明度 0-1，默认 0.5 */
  opacity?: number;
  /** 位置，默认 bottomRight */
  position?: WatermarkPosition;
}

/** 缩略图信息 */
export interface ThumbnailInfo {
  url: string;
  key: string;
  width: number;
  height: number;
  size: number;
}

/** 上传结果 */
export interface UploadResult {
  url: string;
  key: string;
  size: number;
  content_type: string;
  thumbnails?: Record<string, ThumbnailInfo>;
}

/** 上传文件函数签名 */
export type UploadFileFn = (file: File, folder?: string) => Promise<{ url: string; thumbnails?: Record<string, ThumbnailInfo> }>;

/** URL转存函数签名 */
export type TransferUrlFn = (url: string, folder?: string) => Promise<{ url: string }>;

/** 图片上传组件属性 */
export interface ImageUploadProps {
  /** 当前值（图片URL） */
  value?: string;
  /** 值变化回调 */
  onChange?: (value: string | undefined) => void;
  /** 缩略图变化回调（当 generateThumbnails 为 true 时使用） */
  onThumbnailsChange?: (thumbnails: Record<string, ThumbnailInfo> | undefined) => void;
  /** 剪裁比例 */
  aspectRatio?: AspectRatioPreset;
  /** 是否禁用 */
  disabled?: boolean;
  /** 最大文件大小（MB） */
  maxSize?: number;
  /** 存储文件夹 */
  folder?: string;
  /** 提示文字 */
  placeholder?: string;
  /** 图片宽度 */
  width?: number | string;
  /** 图片高度 */
  height?: number | string;
  /** 是否支持URL转存 */
  allowUrlTransfer?: boolean;
  /** 是否显示剪裁按钮 */
  showCrop?: boolean;
  /** 是否生成缩略图 */
  generateThumbnails?: boolean;

  // ===== 裁剪增强属性 =====
  /** 裁剪输出格式，默认 'jpeg' */
  cropOutputFormat?: ImageOutputFormat;
  /** 裁剪背景颜色，'transparent' 表示透明（仅 PNG/WebP 支持），默认 '#ffffff' */
  cropBackgroundColor?: string | 'transparent';
  /** 裁剪输出质量 0-1，默认 0.9 */
  cropQuality?: number;
  /** 裁剪输出最大宽度 */
  cropMaxWidth?: number;
  /** 裁剪输出最大高度 */
  cropMaxHeight?: number;
  /** 是否圆形裁剪 */
  cropCircular?: boolean;
  /** 预设尺寸选项 */
  cropPresetSizes?: PresetSize[];
  /** 是否显示网格辅助线，默认 true */
  cropShowGrid?: boolean;
  /** 是否显示翻转按钮，默认 true */
  cropShowFlip?: boolean;
  /** 是否显示亮度对比度调节，默认 false */
  cropShowBrightnessContrast?: boolean;
  /** 水印配置 */
  cropWatermark?: WatermarkConfig;

  // ===== 依赖注入（消除 @hospital/api 循环依赖） =====
  /** 自定义上传函数，替代内置 uploadApi.upload */
  onUpload?: UploadFileFn;
  /** 自定义URL转存函数，替代内置 uploadApi.transfer */
  onTransferUrl?: TransferUrlFn;
}

/** 图片剪裁组件属性 */
export interface ImageCropperProps {
  /** 是否显示 */
  open: boolean;
  /** 图片源 */
  imageSrc: string;
  /** 剪裁比例 */
  aspectRatio?: number;
  /** 确认回调 */
  onConfirm: (croppedFile: File) => void;
  /** 取消回调 */
  onCancel: () => void;

  // ===== 输出配置 =====
  /** 输出格式，默认 'jpeg' */
  outputFormat?: ImageOutputFormat;
  /** 背景颜色，'transparent' 表示透明（仅 PNG/WebP 支持），默认 '#ffffff' */
  backgroundColor?: string | 'transparent';
  /** 输出质量 0-1，默认 0.9 */
  quality?: number;
  /** 输出最大宽度 */
  maxWidth?: number;
  /** 输出最大高度 */
  maxHeight?: number;

  // ===== 裁剪模式 =====
  /** 是否圆形裁剪 */
  circularCrop?: boolean;
  /** 预设尺寸选项 */
  presetSizes?: PresetSize[];

  // ===== 图像调整 =====
  /** 是否显示亮度对比度调节 */
  showBrightnessContrast?: boolean;

  // ===== 水印 =====
  /** 水印配置 */
  watermark?: WatermarkConfig;

  // ===== UI 选项 =====
  /** 是否显示网格辅助线，默认 true */
  showGrid?: boolean;
  /** 是否显示翻转按钮，默认 true */
  showFlip?: boolean;
}
