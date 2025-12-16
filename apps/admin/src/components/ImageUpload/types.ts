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

/** 上传结果 */
export interface UploadResult {
  url: string;
  key: string;
  size: number;
  content_type: string;
}

/** 图片上传组件属性 */
export interface ImageUploadProps {
  /** 当前值（图片URL） */
  value?: string;
  /** 值变化回调 */
  onChange?: (value: string | undefined) => void;
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
}

