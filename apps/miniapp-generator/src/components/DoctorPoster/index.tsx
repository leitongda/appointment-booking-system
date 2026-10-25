import { View, Text, Image, Canvas } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect, useRef } from 'react';
import { getPosterQrcode } from '@hospital/api';
import { encodeDoctorScene } from '../../utils/scene';
import { useTemplate } from '../../contexts/TemplateContext';
import './index.less';

export interface DoctorPosterProps {
  visible: boolean;
  onClose: () => void;
  doctorName: string;
  doctorTitle?: string;
  specialty?: string;
  /** 医生简介，可能是富文本 HTML，绘制前会剔除标签 */
  introduction?: string;
  /** 头像完整 URL（调用方需先用 getImageUrl 拼接），加载失败时用姓氏首字占位 */
  avatarUrl?: string;
  doctorId: string;
}

/** 画布尺寸（逻辑像素），导出时放大 2 倍保证清晰度 */
const POSTER_WIDTH = 600;
const POSTER_HEIGHT = 960;
const CANVAS_ID = 'doctorPosterCanvas';
/** 小程序码落地页（须与 app.config.ts 已发布页面一致） */
const QR_PAGE = 'packageBooking/pages/doctor/detail';
/** 头像 / 小程序码等远程资源超时时间，超时后走占位降级 */
const RESOURCE_TIMEOUT = 10000;
/** 文案主色兜底（正常情况下使用模板 token） */
const FALLBACK_PRIMARY = '#0E7A5F';
const FALLBACK_PRIMARY_SOFT = '#EAF4EF';

/** 估算字符渲染宽度：ASCII 按半宽、中文等按全宽 */
const getCharWidth = (ch: string, fontSize: number): number => {
  const code = ch.codePointAt(0) || 0;
  if (code < 128) return fontSize * 0.5;
  return fontSize;
};

const measureTextWidth = (text: string, fontSize: number): number => {
  let width = 0;
  for (const ch of Array.from(text)) width += getCharWidth(ch, fontSize);
  return width;
};

/**
 * 按宽度折行：支持显式换行，超出 maxLines 截断并在末行追加省略号
 */
const wrapText = (text: string, fontSize: number, maxWidth: number, maxLines: number): string[] => {
  const paragraphs = (text || '').split('\n');
  const lines: string[] = [];
  let truncated = false;

  for (let p = 0; p < paragraphs.length; p++) {
    if (truncated) break;
    let current = '';
    let currentWidth = 0;
    for (const ch of Array.from(paragraphs[p])) {
      const charWidth = getCharWidth(ch, fontSize);
      if (current && currentWidth + charWidth > maxWidth) {
        lines.push(current);
        current = ch;
        currentWidth = charWidth;
        if (lines.length >= maxLines) {
          truncated = true;
          break;
        }
      } else {
        current += ch;
        currentWidth += charWidth;
      }
    }
    if (truncated) break;
    if (p < paragraphs.length - 1) {
      // 显式换行符：即使空行也占一行
      lines.push(current);
      if (lines.length >= maxLines) truncated = true;
    } else if (current) {
      lines.push(current);
    }
  }

  if (truncated && lines.length > 0) {
    let last = lines[lines.length - 1];
    while (last && measureTextWidth(`${last}…`, fontSize) > maxWidth) {
      last = last.slice(0, -1);
    }
    lines[lines.length - 1] = `${last}…`;
  }
  return lines;
};

/** 简介可能是富文本 HTML，剔除标签与常见实体后再绘制 */
const stripHtml = (html?: string | null): string => {
  return (html || '')
    .replace(/<[^>]*>/g, '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .trim();
};

/** 描述圆角矩形路径 */
const pathRoundRect = (ctx: Taro.CanvasContext, x: number, y: number, w: number, h: number, r: number) => {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arc(x + w - r, y + r, r, -Math.PI / 2, 0);
  ctx.lineTo(x + w, y + h - r);
  ctx.arc(x + w - r, y + h - r, r, 0, Math.PI / 2);
  ctx.lineTo(x + r, y + h);
  ctx.arc(x + r, y + h - r, r, Math.PI / 2, Math.PI);
  ctx.lineTo(x, y + r);
  ctx.arc(x + r, y + r, r, Math.PI, Math.PI * 1.5);
  ctx.closePath();
};

/** 设置字体（legacy canvas 无 setFont 方法，通过 font 属性同时指定字号与字重） */
const applyFont = (ctx: Taro.CanvasContext, fontSize: number, weight: 'normal' | 'bold' = 'normal') => {
  ctx.font = `${weight} ${fontSize}px sans-serif`;
};

/** 居中绘制单行文本（y 为文本顶部） */
const drawCenteredLine = (
  ctx: Taro.CanvasContext,
  text: string,
  fontSize: number,
  weight: 'normal' | 'bold',
  color: string,
  centerX: number,
  top: number,
) => {
  applyFont(ctx, fontSize, weight);
  ctx.setFillStyle(color);
  ctx.setTextAlign('center');
  ctx.fillText(text, centerX, top);
  ctx.setTextAlign('left');
};

/**
 * 医生海报弹层
 * 离屏 Canvas 绘制 600x960 海报 → 导出临时图片预览 → 可保存到相册。
 * 头像 / 小程序码等远程资源加载失败时静默降级为占位，海报始终可生成与保存。
 */
const DoctorPoster: React.FC<DoctorPosterProps> = ({
  visible,
  onClose,
  doctorName,
  doctorTitle,
  specialty,
  introduction,
  avatarUrl,
  doctorId,
}) => {
  const { tokens, tone } = useTemplate();
  const primary = tokens.primary || FALLBACK_PRIMARY;
  const primarySoft = tokens.primarySoft || FALLBACK_PRIMARY_SOFT;
  const orgName = tone.custom?.orgName || '机构介绍';

  const [posterPath, setPosterPath] = useState('');
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);

  // 生成过程中组件卸载 / 弹层关闭时中断后续 setState 与绘制
  const cancelledRef = useRef(false);
  // 所有定时器统一登记，卸载时清理
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const addTimer = (callback: () => void, delay: number): ReturnType<typeof setTimeout> => {
    const timer = setTimeout(callback, delay);
    timersRef.current.push(timer);
    return timer;
  };

  const clearTimers = () => {
    timersRef.current.forEach(timer => clearTimeout(timer));
    timersRef.current = [];
  };

  useEffect(() => {
    return () => {
      cancelledRef.current = true;
      clearTimers();
    };
  }, []);

  /** 带超时的 Promise 竞速，超时按失败处理（走占位降级） */
  const withTimeout = <T,>(promise: Promise<T>, timeout: number): Promise<T> => {
    return new Promise<T>((resolve, reject) => {
      const timer = addTimer(() => reject(new Error('海报资源加载超时')), timeout);
      promise.then(
        value => {
          clearTimeout(timer);
          resolve(value);
        },
        error => {
          clearTimeout(timer);
          reject(error);
        },
      );
    });
  };

  /** 下载头像到临时路径，失败返回空串（绘制首字占位） */
  const loadAvatarTempPath = async (): Promise<string> => {
    if (!avatarUrl) return '';
    try {
      const res = await withTimeout(Taro.downloadFile({ url: avatarUrl }), RESOURCE_TIMEOUT);
      if (res.statusCode === 200 && res.tempFilePath) return res.tempFilePath;
      return '';
    } catch (error) {
      console.error('[医生海报] 头像下载失败，使用文字占位', error);
      return '';
    }
  };

  /** base64 的小程序码写入临时文件（canvas drawImage 不支持 data URL / 裸 base64） */
  const writeBase64ToTempFile = (base64Data: string): string => {
    try {
      const userDataPath = (Taro as any).env?.USER_DATA_PATH as string | undefined;
      if (!base64Data || !userDataPath) return '';
      const filePath = `${userDataPath}/doctor-poster-qrcode-${Date.now()}.png`;
      Taro.getFileSystemManager().writeFileSync(filePath, base64Data, 'base64');
      return filePath;
    } catch (error) {
      console.error('[医生海报] 小程序码写入临时文件失败', error);
      return '';
    }
  };

  /** 获取小程序码临时路径，失败返回空串（绘制灰色占位块） */
  const loadQrcodeTempPath = async (): Promise<string> => {
    // scene 契约见 utils/scene.ts：UUID 去连字符的 32 位十六进制（微信 scene 上限 32 可见字符）
    const scene = encodeDoctorScene(doctorId);
    if (!scene) {
      console.error('[医生海报] 医生ID无法编码为 scene，使用占位', doctorId);
      return '';
    }
    try {
      const result = await withTimeout(
        getPosterQrcode({ scene, page: QR_PAGE }),
        RESOURCE_TIMEOUT,
      );
      const image = (result?.image || '').trim();
      if (!image) return '';
      if (image.startsWith('data:')) {
        // data URL：取逗号后的 base64 部分
        return writeBase64ToTempFile(image.slice(image.indexOf(',') + 1));
      }
      if (/^https?:\/\//.test(image)) {
        // http 地址：下载为临时文件
        const res = await withTimeout(Taro.downloadFile({ url: image }), RESOURCE_TIMEOUT);
        return res.statusCode === 200 ? res.tempFilePath : '';
      }
      // 裸 base64（当前后端契约：PNG 二进制的 base64 字符串）
      return writeBase64ToTempFile(image);
    } catch (error) {
      console.error('[医生海报] 小程序码获取失败，使用占位', error);
      return '';
    }
  };

  /** 绘制海报内容；任何素材缺失都以占位呈现，不抛错 */
  const drawPoster = (avatarTempPath: string, qrcodeTempPath: string): Promise<void> => {
    return new Promise<void>(resolve => {
      const ctx = Taro.createCanvasContext(CANVAS_ID);
      // 供 draw 回调未触发时的兜底（部分平台 canvas 异常时不回调）
      const safetyTimer = addTimer(() => resolve(), POSTER_HEIGHT);

      try {
        // 背景（模板浅色底）
        ctx.setFillStyle(primarySoft);
        ctx.fillRect(0, 0, POSTER_WIDTH, POSTER_HEIGHT);

        // 顶部机构名
        drawCenteredLine(ctx, orgName, 30, 'bold', primary, POSTER_WIDTH / 2, 64);

        // 白色圆角底卡
        ctx.setFillStyle('#FFFFFF');
        pathRoundRect(ctx, 28, 104, POSTER_WIDTH - 56, POSTER_HEIGHT - 128, 28);
        ctx.fill();

        // 圆形头像：白色描边 + 裁剪绘制；失败画姓氏首字圆底占位
        const avatarCenterY = 180;
        const avatarRadius = 72;
        ctx.setFillStyle('#FFFFFF');
        ctx.beginPath();
        ctx.arc(POSTER_WIDTH / 2, avatarCenterY, avatarRadius + 8, 0, Math.PI * 2);
        ctx.fill();
        if (avatarTempPath) {
          ctx.save();
          ctx.beginPath();
          ctx.arc(POSTER_WIDTH / 2, avatarCenterY, avatarRadius, 0, Math.PI * 2);
          ctx.clip();
          ctx.drawImage(avatarTempPath, POSTER_WIDTH / 2 - avatarRadius, avatarCenterY - avatarRadius, avatarRadius * 2, avatarRadius * 2);
          ctx.restore();
        } else {
          ctx.setFillStyle(primarySoft);
          ctx.beginPath();
          ctx.arc(POSTER_WIDTH / 2, avatarCenterY, avatarRadius, 0, Math.PI * 2);
          ctx.fill();
          const initial = Array.from(doctorName || '医')[0] || '医';
          drawCenteredLine(ctx, initial, 56, 'bold', primary, POSTER_WIDTH / 2, avatarCenterY - 28);
        }

        // 姓名 + 职称（单行超宽省略）
        const nameText = doctorTitle ? `${doctorName}·${doctorTitle}` : doctorName;
        const [nameLine] = wrapText(nameText, 38, POSTER_WIDTH - 100, 1);
        if (nameLine) {
          drawCenteredLine(ctx, nameLine, 38, 'bold', '#1F2937', POSTER_WIDTH / 2, 302);
        }

        // 擅长（最多 4 行）
        const specialtyText = stripHtml(specialty);
        if (specialtyText) {
          applyFont(ctx, 30, 'bold');
          ctx.setFillStyle(primary);
          ctx.fillText('擅长', 64, 368);
          const specialtyLines = wrapText(specialtyText, 24, POSTER_WIDTH - 128, 4);
          applyFont(ctx, 24, 'normal');
          ctx.setFillStyle('#4B5563');
          specialtyLines.forEach((line, index) => {
            ctx.fillText(line, 64, 408 + index * 36);
          });
        }

        // 简介摘录（最多 6 行）
        const introductionText = stripHtml(introduction);
        if (introductionText) {
          applyFont(ctx, 30, 'bold');
          ctx.setFillStyle(primary);
          ctx.fillText('简介', 64, 572);
          const introductionLines = wrapText(introductionText, 22, POSTER_WIDTH - 128, 6);
          applyFont(ctx, 22, 'normal');
          ctx.setFillStyle('#4B5563');
          introductionLines.forEach((line, index) => {
            ctx.fillText(line, 64, 612 + index * 32);
          });
        }

        // 底部小程序码 + 提示语
        const qrSize = 104;
        const qrY = 806;
        if (qrcodeTempPath) {
          ctx.drawImage(qrcodeTempPath, 68, qrY, qrSize, qrSize);
        } else {
          // 灰色圆角占位块
          ctx.setFillStyle('#F3F4F6');
          pathRoundRect(ctx, 68, qrY, qrSize, qrSize, 12);
          ctx.fill();
          const placeholderLines = wrapText('小程序码暂未生成', 16, qrSize - 12, 2);
          applyFont(ctx, 16, 'normal');
          ctx.setFillStyle('#9CA3AF');
          placeholderLines.forEach((line, index) => {
            ctx.setTextAlign('center');
            ctx.fillText(line, 68 + qrSize / 2, qrY + 36 + index * 22);
            ctx.setTextAlign('left');
          });
        }
        applyFont(ctx, 22, 'normal');
        ctx.setFillStyle(primary);
        ctx.fillText('长按识别小程序码查看医生详情', 196, qrY + 41);

        ctx.draw(false, () => {
          clearTimeout(safetyTimer);
          resolve();
        });
      } catch (error) {
        console.error('[医生海报] 绘制异常', error);
        clearTimeout(safetyTimer);
        resolve();
      }
    });
  };

  /** 生成海报：下载素材 → 绘制 → 导出临时图片；任一环节失败都保持可预览/可保存的降级路径 */
  const generatePoster = async () => {
    if (cancelledRef.current) return;
    setGenerating(true);
    setPosterPath('');
    try {
      const [avatarTempPath, qrcodeTempPath] = await Promise.all([
        loadAvatarTempPath(),
        loadQrcodeTempPath(),
      ]);
      if (cancelledRef.current) return;
      await drawPoster(avatarTempPath, qrcodeTempPath);
      if (cancelledRef.current) return;
      const result = await Taro.canvasToTempFilePath({
        canvasId: CANVAS_ID,
        x: 0,
        y: 0,
        width: POSTER_WIDTH,
        height: POSTER_HEIGHT,
        destWidth: POSTER_WIDTH * 2,
        destHeight: POSTER_HEIGHT * 2,
        fileType: 'png',
      });
      if (!cancelledRef.current) {
        setPosterPath(result.tempFilePath);
      }
    } catch (error) {
      console.error('[医生海报] 生成失败', error);
    } finally {
      if (!cancelledRef.current) {
        setGenerating(false);
      }
    }
  };

  // 弹层打开后等画布挂载完成再绘制
  useEffect(() => {
    if (!visible) return undefined;
    cancelledRef.current = false;
    addTimer(() => {
      void generatePoster();
    }, 300);
    return () => {
      cancelledRef.current = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible]);

  /** 保存到相册；授权失败时引导去设置页开启 */
  const handleSave = async () => {
    if (!posterPath || saving || generating) return;
    setSaving(true);
    try {
      await Taro.saveImageToPhotosAlbum({ filePath: posterPath });
      Taro.showToast({ title: '已保存到相册', icon: 'success' });
    } catch (error: any) {
      const errMsg = error?.errMsg || '';
      if (/auth|deny|denied|authorize|permission/i.test(errMsg)) {
        Taro.showToast({ title: '未授权相册，请在设置中开启后重试', icon: 'none', duration: 2500 });
      } else if (!/cancel/i.test(errMsg)) {
        Taro.showToast({ title: '保存失败，请重试', icon: 'none' });
      }
    } finally {
      setSaving(false);
    }
  };

  if (!visible) return null;

  return (
    <View className="doctor-poster-mask" onClick={onClose}>
      <View className="doctor-poster-sheet" onClick={e => e.stopPropagation()}>
        <Text className="doctor-poster-close" onClick={onClose} aria-label="关闭海报">
          x
        </Text>

        <View className="doctor-poster-preview">
          {posterPath ? (
            <Image className="doctor-poster-preview-image" src={posterPath} mode="aspectFit" />
          ) : (
            <View className="doctor-poster-loading">
              <Text className="doctor-poster-loading-text">
                {generating ? '海报生成中...' : '海报暂未生成，请关闭后重试'}
              </Text>
            </View>
          )}
        </View>

        <View className="doctor-poster-footer">
          <View
            className={`doctor-poster-save-btn ${posterPath ? '' : 'disabled'}`}
            style={{ backgroundColor: primary }}
            onClick={handleSave}
            aria-label={posterPath ? '保存到相册' : '海报生成中'}
            role="button"
          >
            <Text className="doctor-poster-save-btn-text">
              {generating ? '生成中...' : saving ? '保存中...' : '保存到相册'}
            </Text>
          </View>
        </View>
      </View>

      {/* 离屏画布：仅用于绘制海报，不参与展示 */}
      <Canvas className="doctor-poster-canvas" canvasId={CANVAS_ID} />
    </View>
  );
};

export default DoctorPoster;
