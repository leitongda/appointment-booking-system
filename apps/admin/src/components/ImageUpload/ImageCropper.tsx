/**
 * 图片剪裁组件
 */
import { Modal, Slider, Space, Button } from 'antd';
import { useState, useRef, useCallback, useEffect } from 'react';
import ReactCrop, { type Crop, type PixelCrop, centerCrop, makeAspectCrop } from 'react-image-crop';
import 'react-image-crop/dist/ReactCrop.css';
import type { ImageCropperProps } from './types';

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

const ImageCropper: React.FC<ImageCropperProps> = ({
  open,
  imageSrc,
  aspectRatio,
  onConfirm,
  onCancel,
}) => {
  const imgRef = useRef<HTMLImageElement>(null);
  const [crop, setCrop] = useState<Crop>();
  const [completedCrop, setCompletedCrop] = useState<PixelCrop>();
  const [scale, setScale] = useState(1);
  const [rotate, setRotate] = useState(0);
  const [loading, setLoading] = useState(false);

  // 图片加载完成后初始化剪裁区域
  const onImageLoad = useCallback((e: React.SyntheticEvent<HTMLImageElement>) => {
    const { width, height } = e.currentTarget;
    setCrop(centerAspectCrop(width, height, aspectRatio));
  }, [aspectRatio]);

  // 重置状态
  useEffect(() => {
    if (open) {
      setScale(1);
      setRotate(0);
      setCrop(undefined);
      setCompletedCrop(undefined);
    }
  }, [open]);

  // 执行剪裁
  const handleCrop = async () => {
    if (!imgRef.current || !completedCrop) {
      return;
    }

    setLoading(true);

    try {
      const image = imgRef.current;
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');

      if (!ctx) {
        throw new Error('Canvas context not available');
      }

      // 计算实际的剪裁尺寸
      const scaleX = image.naturalWidth / image.width;
      const scaleY = image.naturalHeight / image.height;

      const pixelRatio = window.devicePixelRatio || 1;

      canvas.width = Math.floor(completedCrop.width * scaleX * pixelRatio);
      canvas.height = Math.floor(completedCrop.height * scaleY * pixelRatio);

      ctx.scale(pixelRatio, pixelRatio);
      ctx.imageSmoothingQuality = 'high';

      const cropX = completedCrop.x * scaleX;
      const cropY = completedCrop.y * scaleY;

      const rotateRads = rotate * (Math.PI / 180);
      const centerX = image.naturalWidth / 2;
      const centerY = image.naturalHeight / 2;

      ctx.save();

      // 移动到画布中心
      ctx.translate(canvas.width / (2 * pixelRatio), canvas.height / (2 * pixelRatio));
      ctx.rotate(rotateRads);
      ctx.scale(scale, scale);
      ctx.translate(-centerX, -centerY);

      // 绘制图片
      ctx.drawImage(
        image,
        cropX,
        cropY,
        completedCrop.width * scaleX,
        completedCrop.height * scaleY,
        centerX - (completedCrop.width * scaleX) / 2,
        centerY - (completedCrop.height * scaleY) / 2,
        completedCrop.width * scaleX,
        completedCrop.height * scaleY
      );

      ctx.restore();

      // 转换为Blob
      const blob = await canvasToBlob(canvas, 'image/jpeg', 0.9);
      const file = new File([blob], 'cropped.jpg', { type: 'image/jpeg' });

      onConfirm(file);
    } catch (error) {
      console.error('Crop error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="图片剪裁"
      open={open}
      onCancel={onCancel}
      width={700}
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
        {/* 剪裁区域 */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          maxHeight: 400, 
          overflow: 'auto',
          background: '#f5f5f5',
          borderRadius: 8,
          padding: 8,
        }}>
          <ReactCrop
            crop={crop}
            onChange={(_, percentCrop) => setCrop(percentCrop)}
            onComplete={(c) => setCompletedCrop(c)}
            aspect={aspectRatio}
            style={{ maxHeight: '100%' }}
          >
            <img
              ref={imgRef}
              src={imageSrc}
              alt="crop"
              style={{
                transform: `scale(${scale}) rotate(${rotate}deg)`,
                maxWidth: '100%',
                maxHeight: 380,
              }}
              onLoad={onImageLoad}
            />
          </ReactCrop>
        </div>

        {/* 控制器 */}
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ width: 60 }}>缩放:</span>
            <Slider
              min={0.5}
              max={2}
              step={0.1}
              value={scale}
              onChange={setScale}
              style={{ flex: 1 }}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ width: 60 }}>旋转:</span>
            <Slider
              min={-180}
              max={180}
              value={rotate}
              onChange={setRotate}
              style={{ flex: 1 }}
            />
          </div>
        </Space>
      </div>
    </Modal>
  );
};

export default ImageCropper;

