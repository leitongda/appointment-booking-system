/**
 * 图片上传卡片组件
 *
 * 功能：
 * - 封装现有的 ImageUpload 组件
 * - 添加卡片布局和标题
 * - 支持裁剪、压缩配置
 * - 统一的样式和布局
 */
import { Card, Form } from 'antd';
import ImageUpload from '@/components/ImageUpload';
import type { AspectRatioPreset, ImageOutputFormat, PresetSize, WatermarkConfig } from '@/components/ImageUpload/types';
import React from 'react';

/**
 * 图片上传卡片组件属性
 */
export interface ImageUploadCardProps {
  /** 卡片标题 */
  title: string;
  /** 表单字段名 */
  name: string;
  /** 剪裁比例 */
  aspectRatio?: AspectRatioPreset;
  /** 图片宽度 */
  width?: number | string;
  /** 图片高度 */
  height?: number | string;
  /** 最大文件大小（MB） */
  maxSize?: number;
  /** 存储文件夹 */
  folder?: string;
  /** 提示文字 */
  placeholder?: string;
  /** 是否显示剪裁按钮 */
  showCrop?: boolean;
  /** 是否支持URL转存 */
  allowUrlTransfer?: boolean;
  /** 是否生成缩略图 */
  generateThumbnails?: boolean;
  /** 是否禁用 */
  disabled?: boolean;
  /** 卡片样式 */
  cardStyle?: React.CSSProperties;
  /** 卡片类名 */
  cardClassName?: string;
  /** 字段 tooltip */
  tooltip?: string;
  /** 字段额外说明 */
  extra?: string;
  /** 是否必填 */
  required?: boolean;
  /** 必填错误提示 */
  requiredMessage?: string;

  // ===== 裁剪增强属性 =====
  /** 裁剪输出格式 */
  cropOutputFormat?: ImageOutputFormat;
  /** 裁剪背景颜色 */
  cropBackgroundColor?: string | 'transparent';
  /** 裁剪输出质量 0-1 */
  cropQuality?: number;
  /** 裁剪输出最大宽度 */
  cropMaxWidth?: number;
  /** 裁剪输出最大高度 */
  cropMaxHeight?: number;
  /** 是否圆形裁剪 */
  cropCircular?: boolean;
  /** 预设尺寸选项 */
  cropPresetSizes?: PresetSize[];
  /** 是否显示网格辅助线 */
  cropShowGrid?: boolean;
  /** 是否显示翻转按钮 */
  cropShowFlip?: boolean;
  /** 是否显示亮度对比度调节 */
  cropShowBrightnessContrast?: boolean;
  /** 水印配置 */
  cropWatermark?: WatermarkConfig;
}

/**
 * 图片上传卡片组件
 *
 * 将 ImageUpload 组件封装在 Card 中，提供统一的布局和样式。
 *
 * @example
 * ```tsx
 * // 基础用法
 * <ImageUploadCard
 *   title="用户头像"
 *   name="avatar"
 *   aspectRatio="1:1"
 *   width={120}
 *   height={120}
 *   folder="avatars"
 * />
 *
 * // Banner 上传
 * <ImageUploadCard
 *   title="医生 Banner"
 *   name="banner"
 *   aspectRatio="16:9"
 *   width={272}
 *   height={153}
 *   folder="doctor"
 *   showCrop={true}
 *   required={true}
 * />
 *
 * // 高级裁剪配置
 * <ImageUploadCard
 *   title="封面图"
 *   name="cover"
 *   aspectRatio="16:9"
 *   cropQuality={0.95}
 *   cropMaxWidth={1920}
 *   cropShowGrid={true}
 *   cropShowFlip={true}
 * />
 * ```
 */
const ImageUploadCard: React.FC<ImageUploadCardProps> = ({
  title,
  name,
  aspectRatio = 'free',
  width = 120,
  height = 120,
  maxSize = 5,
  folder = 'images',
  placeholder = '点击或拖拽上传图片',
  showCrop = true,
  allowUrlTransfer = true,
  generateThumbnails = false,
  disabled = false,
  cardStyle,
  cardClassName,
  tooltip,
  extra,
  required = false,
  requiredMessage = '请上传图片',

  // 裁剪增强属性
  cropOutputFormat,
  cropBackgroundColor,
  cropQuality,
  cropMaxWidth,
  cropMaxHeight,
  cropCircular,
  cropPresetSizes,
  cropShowGrid,
  cropShowFlip,
  cropShowBrightnessContrast,
  cropWatermark,
}) => {
  return (
    <Card
      title={title}
      style={{ marginBottom: 16, ...cardStyle }}
      className={cardClassName}
    >
      <Form.Item
        name={name}
        valuePropName="value"
        tooltip={tooltip}
        extra={extra}
        rules={required ? [{ required: true, message: requiredMessage }] : undefined}
      >
        <ImageUpload
          aspectRatio={aspectRatio}
          width={width}
          height={height}
          maxSize={maxSize}
          folder={folder}
          placeholder={placeholder}
          showCrop={showCrop}
          allowUrlTransfer={allowUrlTransfer}
          generateThumbnails={generateThumbnails}
          disabled={disabled}
          // 裁剪增强属性
          cropOutputFormat={cropOutputFormat}
          cropBackgroundColor={cropBackgroundColor}
          cropQuality={cropQuality}
          cropMaxWidth={cropMaxWidth}
          cropMaxHeight={cropMaxHeight}
          cropCircular={cropCircular}
          cropPresetSizes={cropPresetSizes}
          cropShowGrid={cropShowGrid}
          cropShowFlip={cropShowFlip}
          cropShowBrightnessContrast={cropShowBrightnessContrast}
          cropWatermark={cropWatermark}
        />
      </Form.Item>
    </Card>
  );
};

export default ImageUploadCard;
