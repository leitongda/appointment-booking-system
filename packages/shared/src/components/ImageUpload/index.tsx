/**
 * 图片上传组件
 *
 * 功能：
 * - 点击/拖拽上传
 * - 图片预览
 * - 图片剪裁
 * - URL转存
 */
import { Upload, Button, Space, Input, App, Image } from 'antd';
import { PlusOutlined, DeleteOutlined, ScissorOutlined, LinkOutlined, LoadingOutlined } from '@ant-design/icons';
import { useState, useCallback } from 'react';
import type { ChangeEvent } from 'react';
import type { UploadProps } from 'antd';
import ImageCropper from './ImageCropper';
import type { ImageUploadProps } from './types';
import { ASPECT_RATIO_MAP } from './types';

export type * from './types';
export { default as ImageCropper } from './ImageCropper';

type BeforeUploadFile = Parameters<NonNullable<UploadProps['beforeUpload']>>[0];

const ImageUpload = ({
  value,
  onChange,
  onThumbnailsChange,
  aspectRatio = 'free',
  disabled = false,
  maxSize = 5,
  folder = 'images',
  placeholder = '点击或拖拽上传图片',
  width = 120,
  height = 120,
  allowUrlTransfer = true,
  showCrop = true,
  generateThumbnails = false,
  // 裁剪增强属性
  cropOutputFormat = 'jpeg',
  cropBackgroundColor = '#ffffff',
  cropQuality = 0.9,
  cropMaxWidth,
  cropMaxHeight,
  cropCircular = false,
  cropPresetSizes,
  cropShowGrid = true,
  cropShowFlip = true,
  cropShowBrightnessContrast = false,
  cropWatermark,
  // 依赖注入
  onUpload,
  onTransferUrl,
}: ImageUploadProps) => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [cropperOpen, setCropperOpen] = useState(false);
  const [cropperSrc, setCropperSrc] = useState('');
  const [urlInputVisible, setUrlInputVisible] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [urlTransferring, setUrlTransferring] = useState(false);

  // 获取剪裁比例数值
  const aspectRatioValue = ASPECT_RATIO_MAP[aspectRatio];

  // 上传 API（必须通过 onUpload 注入，避免循环依赖）

  // 上传文件
  const uploadFile = useCallback(async (file: File) => {
    setLoading(true);
    try {
      let result: { url: string; thumbnails?: Record<string, import('./types').ThumbnailInfo> };
      if (!onUpload) {
        throw new Error('请提供 onUpload 属性');
      }
      result = await onUpload(file, folder);
      onChange?.(result.url);
      // 如果有缩略图，通知父组件
      if (result.thumbnails && onThumbnailsChange) {
        onThumbnailsChange(result.thumbnails);
      }
      message.success('上传成功');
    } catch (error: any) {
      message.error(error.message || '上传失败');
    } finally {
      setLoading(false);
    }
  }, [folder, onChange, onThumbnailsChange, message, onUpload]);

  // 处理文件选择（开始剪裁或直接上传）
  const handleFileSelect = useCallback<NonNullable<UploadProps['beforeUpload']>>((file: BeforeUploadFile) => {
    const imageFile = file as unknown as File;

    // 检查文件大小
    if (imageFile.size > maxSize * 1024 * 1024) {
      message.error(`文件大小不能超过 ${maxSize}MB`);
      return false;
    }

    // 检查文件类型
    if (!imageFile.type.startsWith('image/')) {
      message.error('请选择图片文件');
      return false;
    }

    if (showCrop && aspectRatio !== 'free') {
      // 需要剪裁，显示剪裁弹窗
      const reader = new FileReader();
      reader.onload = () => {
        setCropperSrc(reader.result as string);
        setCropperOpen(true);
      };
      reader.readAsDataURL(imageFile);
    } else {
      // 不需要剪裁，直接上传
      uploadFile(imageFile);
    }

    return false; // 阻止默认上传行为
  }, [maxSize, showCrop, aspectRatio, uploadFile, message]);

  // 剪裁确认
  const handleCropConfirm = useCallback((croppedFile: File) => {
    setCropperOpen(false);
    uploadFile(croppedFile);
  }, [uploadFile]);

  // 剪裁取消
  const handleCropCancel = useCallback(() => {
    setCropperOpen(false);
    setCropperSrc('');
  }, []);

  // URL转存
  const handleUrlTransfer = useCallback(async () => {
    if (!urlInput.trim()) {
      message.error('请输入图片URL');
      return;
    }

    // 简单的URL格式验证
    try {
      new URL(urlInput);
    } catch {
      message.error('请输入有效的URL');
      return;
    }

    setUrlTransferring(true);
    try {
      if (!onTransferUrl) {
        throw new Error('请提供 onTransferUrl 属性');
      }
      const result = await onTransferUrl(urlInput.trim(), folder);
      onChange?.(result.url);
      setUrlInputVisible(false);
      setUrlInput('');
      message.success('转存成功');
    } catch (error: any) {
      message.error(error.message || '转存失败');
    } finally {
      setUrlTransferring(false);
    }
  }, [urlInput, folder, onChange, message, onTransferUrl]);

  // 删除图片
  const handleDelete = useCallback(() => {
    onChange?.(undefined);
    onThumbnailsChange?.(undefined);
  }, [onChange, onThumbnailsChange]);

  // 重新剪裁当前图片
  const handleReCrop = useCallback(() => {
    if (value) {
      setCropperSrc(value);
      setCropperOpen(true);
    }
  }, [value]);

  // 上传配置
  const uploadProps: UploadProps = {
    accept: 'image/*',
    showUploadList: false,
    beforeUpload: handleFileSelect,
    disabled: disabled || loading,
  } as UploadProps;

  // 渲染上传区域
  const renderUploadArea = () => {
    if (value) {
      // 已有图片，显示预览
      return (
        <div style={{
          position: 'relative',
          width,
          height,
          display: 'inline-block',
          border: '1px solid #d9d9d9',
          borderRadius: 8,
          overflow: 'hidden',
        }}>
          <Image
            src={value}
            alt="preview"
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            preview={{ mask: '预览' }}
          />
          {!disabled && (
            <div style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              background: 'rgba(0,0,0,0.5)',
              padding: '4px 0',
              display: 'flex',
              justifyContent: 'center',
              gap: 8,
            }}>
              {showCrop && (
                <ScissorOutlined
                  style={{ color: '#fff', cursor: 'pointer' }}
                  onClick={handleReCrop}
                  title="重新剪裁"
                />
              )}
              <DeleteOutlined
                style={{ color: '#fff', cursor: 'pointer' }}
                onClick={handleDelete}
                title="删除"
              />
            </div>
          )}
        </div>
      );
    }

    // 无图片，显示上传按钮
    return (
      <Upload.Dragger {...uploadProps} style={{ width, height, padding: 0 }}>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: typeof height === 'number' ? height - 2 : height,
          padding: 8,
        }}>
          {loading ? (
            <LoadingOutlined style={{ fontSize: 24 }} />
          ) : (
            <>
              <PlusOutlined style={{ fontSize: 24, color: '#999' }} />
              <div style={{ marginTop: 8, color: '#999', fontSize: 12, textAlign: 'center' }}>
                {placeholder}
              </div>
            </>
          )}
        </div>
      </Upload.Dragger>
    );
  };

  return (
    <div>
      <Space size={8}>
        {renderUploadArea()}

        {/* URL转存输入 */}
        {allowUrlTransfer && !disabled && (
          urlInputVisible ? (
            <Space.Compact style={{ width: '100%' }}>
              <Input
                placeholder="输入图片URL"
                value={urlInput}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setUrlInput(e.target.value)}
                onPressEnter={handleUrlTransfer}
                disabled={urlTransferring}
              />
              <Button
                type="primary"
                loading={urlTransferring}
                onClick={handleUrlTransfer}
              >
                转存
              </Button>
              <Button onClick={() => { setUrlInputVisible(false); setUrlInput(''); }}>
                取消
              </Button>
            </Space.Compact>
          ) : (
            <Button
              type="link"
              icon={<LinkOutlined />}
              onClick={() => setUrlInputVisible(true)}
              style={{ padding: 0 }}
            >
              从URL导入
            </Button>
          )
        )}
      </Space>

      {/* 剪裁弹窗 */}
      <ImageCropper
        open={cropperOpen}
        imageSrc={cropperSrc}
        aspectRatio={aspectRatioValue}
        onConfirm={handleCropConfirm}
        onCancel={handleCropCancel}
        // 裁剪增强属性
        outputFormat={cropOutputFormat}
        backgroundColor={cropBackgroundColor}
        quality={cropQuality}
        maxWidth={cropMaxWidth}
        maxHeight={cropMaxHeight}
        circularCrop={cropCircular}
        presetSizes={cropPresetSizes}
        showGrid={cropShowGrid}
        showFlip={cropShowFlip}
        showBrightnessContrast={cropShowBrightnessContrast}
        watermark={cropWatermark}
      />
    </div>
  );
};

export default ImageUpload;
