/**
 * 图片剪裁组件
 *
 * 功能：
 * - 基础剪裁（缩放、旋转）
 * - 圆形剪裁
 * - 输出格式选择（JPEG/PNG/WebP）
 * - 透明/自定义背景色
 * - 翻转（水平/垂直）
 * - 亮度/对比度调节
 * - 网格辅助线
 * - 预设尺寸
 * - 水印
 * - 输出尺寸限制
 */
import { Modal, Slider, Space, Button, Select, Tooltip, Segmented } from 'antd';
import {
  AppstoreOutlined,
  ColumnWidthOutlined,
  ColumnHeightOutlined,
} from '@ant-design/icons';
import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import ReactCrop, { type Crop, type PixelCrop, centerCrop, makeAspectCrop } from 'react-image-crop';
import 'react-image-crop/dist/ReactCrop.css';
import type { ImageCropperProps, ImageOutputFormat } from './types';

/** MIME 类型映射 */
const MIME_TYPE_MAP: Record<ImageOutputFormat, string> = {
  jpeg: 'image/jpeg',
  png: 'image/png',
  webp: 'image/webp',
};

/** 文件扩展名映射 */
const EXTENSION_MAP: Record<ImageOutputFormat, string> = {
  jpeg: 'jpg',
  png: 'png',
  webp: 'webp',
};

/**
 * 将canvas内容转换为Blob
 */
function canvasToBlob(canvas: HTMLCanvasElement, type: string = 'image/jpeg', quality: number = 0.9): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) {
          resolve(blob);
        } else {
          reject(new Error('Canvas to Blob failed'));
        }
      },
      type,
      quality
    );
  });
}

/**
 * 生成居中的剪裁区域
 */
function centerAspectCrop(
  mediaWidth: number,
  mediaHeight: number,
  aspect: number | undefined
): Crop {
  if (!aspect) {
    // 自由剪裁模式，默认选中80%区域
    return {
      unit: '%',
      x: 10,
      y: 10,
      width: 80,
      height: 80,
    };
  }

  return centerCrop(
    makeAspectCrop(
      {
        unit: '%',
        width: 90,
      },
      aspect,
      mediaWidth,
      mediaHeight
    ),
    mediaWidth,
    mediaHeight
  );
}

/**
 * 计算水印位置
 */
function getWatermarkPosition(
  position: string,
  canvasWidth: number,
  canvasHeight: number,
  textWidth: number,
  textHeight: number,
  padding: number = 10
): { x: number; y: number } {
  switch (position) {
    case 'topLeft':
      return { x: padding, y: textHeight + padding };
    case 'topRight':
      return { x: canvasWidth - textWidth - padding, y: textHeight + padding };
    case 'bottomLeft':
      return { x: padding, y: canvasHeight - padding };
    case 'bottomRight':
      return { x: canvasWidth - textWidth - padding, y: canvasHeight - padding };
    case 'center':
      return { x: (canvasWidth - textWidth) / 2, y: (canvasHeight + textHeight) / 2 };
    default:
      return { x: canvasWidth - textWidth - padding, y: canvasHeight - padding };
  }
}

const ImageCropper: React.FC<ImageCropperProps> = ({
  open,
  imageSrc,
  aspectRatio: initialAspectRatio,
  onConfirm,
  onCancel,
  // 输出配置
  outputFormat = 'jpeg',
  backgroundColor = '#ffffff',
  quality = 0.9,
  maxWidth,
  maxHeight,
  // 裁剪模式
  circularCrop = false,
  presetSizes,
  // 图像调整
  showBrightnessContrast = false,
  // 水印
  watermark,
  // UI 选项
  showGrid = true,
  showFlip = true,
}) => {
  const imgRef = useRef<HTMLImageElement>(null);
  const [crop, setCrop] = useState<Crop>();
  const [completedCrop, setCompletedCrop] = useState<PixelCrop>();
  const [scale, setScale] = useState(1);
  const [rotate, setRotate] = useState(0);
  const [loading, setLoading] = useState(false);

  // 新增状态
  const [flipH, setFlipH] = useState(false);
  const [flipV, setFlipV] = useState(false);
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [gridVisible, setGridVisible] = useState(showGrid);
  const [currentFormat, setCurrentFormat] = useState<ImageOutputFormat>(outputFormat);
  const [selectedPreset, setSelectedPreset] = useState<string | undefined>();

  // 当前使用的比例（可能被预设尺寸覆盖）
  const [currentAspectRatio, setCurrentAspectRatio] = useState<number | undefined>(
    circularCrop ? 1 : initialAspectRatio
  );

  // 圆形剪裁强制 1:1 比例
  const effectiveAspectRatio = circularCrop ? 1 : currentAspectRatio;

  // 图片加载完成后初始化剪裁区域
  const onImageLoad = useCallback((e: React.SyntheticEvent<HTMLImageElement>) => {
    const { width, height } = e.currentTarget;
    setCrop(centerAspectCrop(width, height, effectiveAspectRatio));
  }, [effectiveAspectRatio]);

  // 重置状态
  useEffect(() => {
    if (open) {
      setScale(1);
      setRotate(0);
      setFlipH(false);
      setFlipV(false);
      setBrightness(100);
      setContrast(100);
      setCrop(undefined);
      setCompletedCrop(undefined);
      setCurrentFormat(outputFormat);
      setGridVisible(showGrid);
      setSelectedPreset(undefined);
      setCurrentAspectRatio(circularCrop ? 1 : initialAspectRatio);
    }
  }, [open, outputFormat, showGrid, circularCrop, initialAspectRatio]);

  // 处理预设尺寸变化
  const handlePresetChange = useCallback((value: string) => {
    setSelectedPreset(value);
    if (!value || !presetSizes) {
      setCurrentAspectRatio(circularCrop ? 1 : initialAspectRatio);
      return;
    }

    const preset = presetSizes.find(p => `${p.width}x${p.height}` === value);
    if (preset) {
      const newAspect = preset.width / preset.height;
      setCurrentAspectRatio(newAspect);

      // 更新裁剪区域
      if (imgRef.current) {
        const { width, height } = imgRef.current;
        setCrop(centerAspectCrop(width, height, newAspect));
      }
    }
  }, [presetSizes, circularCrop, initialAspectRatio]);

  // 预设尺寸选项
  const presetOptions = useMemo(() => {
    if (!presetSizes) return [];
    return presetSizes.map(size => ({
      value: `${size.width}x${size.height}`,
      label: `${size.label} (${size.width}×${size.height})`,
    }));
  }, [presetSizes]);

  // 执行剪裁（两阶段处理：先变换原图，再提取裁剪区域）
  const handleCrop = async () => {
    if (!imgRef.current || !completedCrop) {
      return;
    }

    setLoading(true);

    try {
      const image = imgRef.current;

      // 计算裁剪区域在原图上的实际坐标
      const scaleX = image.naturalWidth / image.width;
      const scaleY = image.naturalHeight / image.height;

      const cropX = completedCrop.x * scaleX;
      const cropY = completedCrop.y * scaleY;
      const cropWidth = completedCrop.width * scaleX;
      const cropHeight = completedCrop.height * scaleY;

      // 计算最终输出尺寸（应用尺寸限制）
      let outputWidth = Math.floor(cropWidth);
      let outputHeight = Math.floor(cropHeight);

      if (maxWidth && outputWidth > maxWidth) {
        const ratio = maxWidth / outputWidth;
        outputWidth = maxWidth;
        outputHeight = Math.floor(outputHeight * ratio);
      }
      if (maxHeight && outputHeight > maxHeight) {
        const ratio = maxHeight / outputHeight;
        outputHeight = maxHeight;
        outputWidth = Math.floor(outputWidth * ratio);
      }

      // ============ 阶段一：在临时 canvas 上变换原图 ============
      const tempCanvas = document.createElement('canvas');
      const tempCtx = tempCanvas.getContext('2d');

      if (!tempCtx) {
        throw new Error('Temporary canvas context not available');
      }

      tempCanvas.width = image.naturalWidth;
      tempCanvas.height = image.naturalHeight;
      tempCtx.imageSmoothingQuality = 'high';

      const centerNaturalX = image.naturalWidth / 2;
      const centerNaturalY = image.naturalHeight / 2;

      tempCtx.save();

      // 应用变换（以原图中心为基准）
      tempCtx.translate(centerNaturalX, centerNaturalY);
      tempCtx.rotate(rotate * (Math.PI / 180));
      tempCtx.scale(scale * (flipH ? -1 : 1), scale * (flipV ? -1 : 1));
      tempCtx.translate(-centerNaturalX, -centerNaturalY);

      // 应用滤镜
      if (brightness !== 100 || contrast !== 100) {
        tempCtx.filter = `brightness(${brightness}%) contrast(${contrast}%)`;
      }

      // 绘制原图到临时 canvas
      tempCtx.drawImage(image, 0, 0, image.naturalWidth, image.naturalHeight);

      tempCtx.restore();

      // ============ 阶段二：从临时 canvas 提取裁剪区域 ============
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');

      if (!ctx) {
        throw new Error('Final canvas context not available');
      }

      canvas.width = outputWidth;
      canvas.height = outputHeight;
      ctx.imageSmoothingQuality = 'high';

      // 填充背景
      const needsBackground = currentFormat === 'jpeg' || backgroundColor !== 'transparent';
      if (needsBackground) {
        const fillColor = backgroundColor === 'transparent' ? '#ffffff' : backgroundColor;
        ctx.fillStyle = fillColor;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }

      // 圆形裁剪
      if (circularCrop) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(outputWidth / 2, outputHeight / 2, Math.min(outputWidth, outputHeight) / 2, 0, Math.PI * 2);
        ctx.clip();
      }

      // 从临时 canvas 提取裁剪区域
      ctx.drawImage(
        tempCanvas,
        cropX, cropY, cropWidth, cropHeight,
        0, 0, outputWidth, outputHeight
      );

      if (circularCrop) {
        ctx.restore();
      }

      // 绘制水印
      if (watermark?.text) {
        ctx.save();
        const fontSize = watermark.fontSize || 16;
        ctx.font = `${fontSize}px sans-serif`;
        ctx.fillStyle = watermark.color || 'rgba(255,255,255,0.8)';
        ctx.globalAlpha = watermark.opacity ?? 0.5;

        const textMetrics = ctx.measureText(watermark.text);
        const textWidth = textMetrics.width;
        const textHeight = fontSize;

        const { x, y } = getWatermarkPosition(
          watermark.position || 'bottomRight',
          outputWidth,
          outputHeight,
          textWidth,
          textHeight
        );

        ctx.fillText(watermark.text, x, y);
        ctx.restore();
      }

      // 转换为 Blob
      const mimeType = MIME_TYPE_MAP[currentFormat];
      const extension = EXTENSION_MAP[currentFormat];
      const blob = await canvasToBlob(canvas, mimeType, quality);
      const file = new File([blob], `cropped.${extension}`, { type: mimeType });

      onConfirm(file);
    } catch (error) {
      console.error('Crop error:', error);
    } finally {
      setLoading(false);
    }
  };

  // 计算图片样式
  const imageStyle = useMemo(() => ({
    transform: `scale(${scale}) rotate(${rotate}deg) scaleX(${flipH ? -1 : 1}) scaleY(${flipV ? -1 : 1})`,
    filter: `brightness(${brightness}%) contrast(${contrast}%)`,
    maxWidth: '100%',
    maxHeight: 380,
  }), [scale, rotate, flipH, flipV, brightness, contrast]);

  return (
    <Modal
      title="图片剪裁"
      open={open}
      onCancel={onCancel}
      width={750}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button key="confirm" type="primary" loading={loading} onClick={handleCrop}>
          确定
        </Button>,
      ]}
      destroyOnHidden
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* 工具栏 */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          flexWrap: 'wrap',
          padding: '8px 0',
          borderBottom: '1px solid #f0f0f0',
        }}>
          {/* 预设尺寸 */}
          {presetSizes && presetSizes.length > 0 && (
            <Select
              placeholder="预设尺寸"
              style={{ width: 180 }}
              allowClear
              value={selectedPreset}
              onChange={handlePresetChange}
              options={presetOptions}
              disabled={circularCrop}
            />
          )}

          {/* 格式选择 */}
          <Segmented
            value={currentFormat}
            onChange={(value) => setCurrentFormat(value as ImageOutputFormat)}
            options={[
              { label: 'JPG', value: 'jpeg' },
              { label: 'PNG', value: 'png' },
              { label: 'WebP', value: 'webp' },
            ]}
          />

          {/* 网格开关 */}
          <Tooltip title={gridVisible ? '隐藏网格' : '显示网格'}>
            <Button
              type={gridVisible ? 'primary' : 'default'}
              icon={<AppstoreOutlined />}
              onClick={() => setGridVisible(!gridVisible)}
            />
          </Tooltip>

          {/* 翻转按钮 */}
          {showFlip && (
            <>
              <Tooltip title="水平翻转">
                <Button
                  type={flipH ? 'primary' : 'default'}
                  icon={<ColumnWidthOutlined />}
                  onClick={() => setFlipH(!flipH)}
                />
              </Tooltip>
              <Tooltip title="垂直翻转">
                <Button
                  type={flipV ? 'primary' : 'default'}
                  icon={<ColumnHeightOutlined />}
                  onClick={() => setFlipV(!flipV)}
                />
              </Tooltip>
            </>
          )}

          {/* 圆形裁剪标识 */}
          {circularCrop && (
            <span style={{
              padding: '2px 8px',
              background: '#1677ff',
              color: '#fff',
              borderRadius: 4,
              fontSize: 12,
            }}>
              圆形
            </span>
          )}
        </div>

        {/* 剪裁区域 */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          maxHeight: 400,
          overflow: 'auto',
          background: '#f5f5f5',
          borderRadius: 8,
          padding: 8,
          position: 'relative',
        }}>
          <ReactCrop
            crop={crop}
            onChange={(_, percentCrop) => setCrop(percentCrop)}
            onComplete={(c) => setCompletedCrop(c)}
            aspect={effectiveAspectRatio}
            circularCrop={circularCrop}
            style={{ maxHeight: '100%' }}
          >
            <div style={{ position: 'relative' }}>
              <img
                ref={imgRef}
                src={imageSrc}
                alt="crop"
                style={imageStyle}
                onLoad={onImageLoad}
              />
              {/* 网格辅助线 */}
              {gridVisible && crop && (
                <div
                  style={{
                    position: 'absolute',
                    left: `${crop.unit === '%' ? crop.x : (crop.x / (imgRef.current?.width || 1)) * 100}%`,
                    top: `${crop.unit === '%' ? crop.y : (crop.y / (imgRef.current?.height || 1)) * 100}%`,
                    width: `${crop.unit === '%' ? crop.width : (crop.width / (imgRef.current?.width || 1)) * 100}%`,
                    height: `${crop.unit === '%' ? crop.height : (crop.height / (imgRef.current?.height || 1)) * 100}%`,
                    pointerEvents: 'none',
                    backgroundImage: `
                      linear-gradient(to right, rgba(255,255,255,0.4) 1px, transparent 1px),
                      linear-gradient(to bottom, rgba(255,255,255,0.4) 1px, transparent 1px)
                    `,
                    backgroundSize: '33.33% 33.33%',
                    backgroundPosition: '0 0',
                    zIndex: 10,
                  }}
                />
              )}
            </div>
          </ReactCrop>
        </div>

        {/* 控制器 */}
        <Space style={{ width: '100%' }} size={8}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ width: 70, flexShrink: 0 }}>缩放:</span>
            <Slider
              min={0.5}
              max={2}
              step={0.1}
              value={scale}
              onChange={setScale}
              style={{ flex: 1 }}
            />
            <span style={{ width: 40, textAlign: 'right' }}>{scale.toFixed(1)}x</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ width: 70, flexShrink: 0 }}>旋转:</span>
            <Slider
              min={-180}
              max={180}
              value={rotate}
              onChange={setRotate}
              style={{ flex: 1 }}
            />
            <span style={{ width: 40, textAlign: 'right' }}>{rotate}°</span>
          </div>

          {/* 亮度对比度调节 */}
          {showBrightnessContrast && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <span style={{ width: 70, flexShrink: 0 }}>亮度:</span>
                <Slider
                  min={50}
                  max={150}
                  value={brightness}
                  onChange={setBrightness}
                  style={{ flex: 1 }}
                />
                <span style={{ width: 40, textAlign: 'right' }}>{brightness}%</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <span style={{ width: 70, flexShrink: 0 }}>对比度:</span>
                <Slider
                  min={50}
                  max={150}
                  value={contrast}
                  onChange={setContrast}
                  style={{ flex: 1 }}
                />
                <span style={{ width: 40, textAlign: 'right' }}>{contrast}%</span>
              </div>
            </>
          )}
        </Space>

        {/* 格式提示 */}
        {currentFormat !== 'jpeg' && backgroundColor === 'transparent' && (
          <div style={{
            padding: '8px 12px',
            background: '#e6f7ff',
            borderRadius: 4,
            fontSize: 12,
            color: '#1677ff',
          }}>
            提示：当前使用 {currentFormat.toUpperCase()} 格式，支持透明背景
          </div>
        )}
        {currentFormat === 'jpeg' && backgroundColor === 'transparent' && (
          <div style={{
            padding: '8px 12px',
            background: '#fff7e6',
            borderRadius: 4,
            fontSize: 12,
            color: '#fa8c16',
          }}>
            提示：JPEG 格式不支持透明背景，将使用白色背景
          </div>
        )}
      </div>
    </Modal>
  );
};

export default ImageCropper;
