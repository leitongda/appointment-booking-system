/**
 * 预览二维码弹窗 — 生成小程序体验二维码并展示。
 *
 * 功能:
 * 1. 二维码图片展示
 * 2. 过期倒计时 (基于 expires_at 实时计算)
 * 3. 使用说明文案
 * 4. 一键刷新 (重新生成二维码)
 * 5. 加载态 & 错误态
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {Button, Image, Modal, Result, Space, Spin, Typography} from 'antd';
import {QrcodeOutlined, ReloadOutlined, ClockCircleOutlined, InfoCircleOutlined} from '@ant-design/icons';
import dayjs from 'dayjs';
import {lowcodeApi, type PreviewQrResponse} from '@hospital/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PreviewQRCodeProps {
  /** 弹窗可见性 */
  open: boolean;
  /** 关闭弹窗 */
  onClose: () => void;
  /** 低代码页面 ID */
  pageId: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** 从 expires_at ISO 字符串计算剩余秒数，返回 0 代表已过期或无过期时间 */
function getRemainingSeconds(expiresAt: string | null): number {
  if (!expiresAt) return 0;
  const diff = Math.floor((dayjs(expiresAt).valueOf() - Date.now()) / 1000);
  return Math.max(0, diff);
}

/** 将秒数格式化为 mm:ss */
function formatCountdown(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

// ---------------------------------------------------------------------------
// PreviewQRCode
// ---------------------------------------------------------------------------

const PreviewQRCode: React.FC<PreviewQRCodeProps> = ({ open, onClose, pageId }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<PreviewQrResponse | null>(null);

  /** 剩余过期秒数 */
  const [remaining, setRemaining] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // --- Fetch ---

  const fetchQrCode = useCallback(async () => {
    if (!pageId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await lowcodeApi.generatePreviewQr(pageId);
      setPreviewData(res);
      setRemaining(getRemainingSeconds(res.expires_at));
    } catch (err: any) {
      setError(err?.message || '生成预览二维码失败');
      setPreviewData(null);
      setRemaining(0);
    } finally {
      setLoading(false);
    }
  }, [pageId]);

  /** 打开弹窗时自动加载 */
  useEffect(() => {
    if (open) {
      fetchQrCode();
    } else {
      setPreviewData(null);
      setError(null);
      setRemaining(0);
    }
  }, [open, fetchQrCode]);

  // --- 倒计时 ---

  useEffect(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    if (remaining > 0 && previewData) {
      timerRef.current = setInterval(() => {
        setRemaining((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current!);
            timerRef.current = null;
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [remaining > 0, !!previewData]);

  // --- Derived ---

  const isExpired = remaining <= 0 && previewData != null && previewData.expires_at != null;

  // --- Render ---

  return (
    <Modal
      title={
        <Space>
          <QrcodeOutlined />
          <span>小程序预览</span>
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={
        <Space>
          <Button onClick={onClose}>关闭</Button>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={fetchQrCode}
            loading={loading}
          >
            刷新二维码
          </Button>
        </Space>
      }
      destroyOnClose
      width={400}
    >
      <Spin spinning={loading} tip="正在生成二维码...">
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          {/* === 加载前 & 加载中 === */}
          {loading && !previewData && (
            <div style={{ minHeight: 200 }} />
          )}

          {/* === 错误态 === */}
          {!loading && error && (
            <Result
              status="error"
              title="生成失败"
              subTitle={error}
              extra={
                <Button icon={<ReloadOutlined />} onClick={fetchQrCode}>
                  重试
                </Button>
              }
            />
          )}

          {/* === 成功态 === */}
          {!loading && previewData && (
            <Space direction="vertical" align="center" size={16} style={{ width: '100%' }}>
              {/* 二维码图片 */}
              <div
                style={{
                  border: '1px solid var(--color-border-secondary)',
                  borderRadius: 8,
                  padding: 16,
                  background: 'var(--color-white)',
                  display: 'inline-block',
                }}
              >
                <Image
                  src={previewData.qr_code_url}
                  alt="小程序预览二维码"
                  width={200}
                  height={200}
                  preview={false}
                  style={{ borderRadius: 4 }}
                  fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mN8/+F/PQAJhAN6o2UzQQAAAABJRU5ErkJggg=="
                />
              </div>

              {/* 服务器返回的提示消息 */}
              {previewData.message && (
                <Typography.Text type="secondary" style={{ fontSize: 13 }}>
                  {previewData.message}
                </Typography.Text>
              )}

              {/* 过期倒计时 */}
              {previewData.expires_at && (
                <div>
                  {isExpired ? (
                    <Space size={4}>
                      <ClockCircleOutlined style={{ color: 'var(--color-error)' }} />
                      <Typography.Text type="danger" style={{ fontSize: 13 }}>
                        二维码已过期，请点击「刷新二维码」重新生成
                      </Typography.Text>
                    </Space>
                  ) : (
                    <Space size={4}>
                      <ClockCircleOutlined style={{ color: 'var(--color-warning)' }} />
                      <Typography.Text type="warning" style={{ fontSize: 13 }}>
                        剩余有效时间: {formatCountdown(remaining)}
                      </Typography.Text>
                    </Space>
                  )}
                </div>
              )}

              {/* 使用说明 */}
              <div
                style={{
                  width: '100%',
                  background: '#f6f8fa',
                  borderRadius: 6,
                  padding: '12px 16px',
                  textAlign: 'left',
                }}
              >
                <Space size={4} style={{ marginBottom: 8 }}>
                  <InfoCircleOutlined style={{ color: 'var(--color-primary)' }} />
                  <Typography.Text strong style={{ fontSize: 13 }}>
                    使用说明
                  </Typography.Text>
                </Space>
                <ol
                  style={{
                    margin: 0,
                    paddingLeft: 20,
                    fontSize: 12,
                    color: 'var(--color-text-secondary)',
                    lineHeight: 2,
                  }}
                >
                  <li>打开微信，使用「扫一扫」扫描上方二维码</li>
                  <li>在微信中选择「预览」打开小程序</li>
                  <li>预览链接有时效性，过期后需重新生成</li>
                </ol>
              </div>
            </Space>
          )}
        </div>
      </Spin>
    </Modal>
  );
};

export default PreviewQRCode;
