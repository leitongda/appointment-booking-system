/**
 * 热力图 - Phase 3
 *
 * 对应后端：GET /api/v1/session-events/heatmap
 *   入参：pagePath / eventType(click|move) / viewportBucket(lg|md|sm) / days
 *   出参：{ pagePath, viewportBucket, eventType, points: [{ xRatio, yRatio, weight }] }
 *
 * 渲染：heatmap.js（h337.create）在空白 canvas 容器上绘制热力图。
 *   points 映射：x = xRatio * W, y = yRatio * H, value = weight。
 *   W/H 取代表性 admin 画布尺寸（按视口分桶）。
 *
 * 备注：v1 在空白画布渲染，未来增强可叠加真实页面截图作背景。
 */
import { PageContainer } from '@ant-design/pro-components';
import { Alert, Card, Empty, Input, Result, Select, Spin, Space, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
// @ts-ignore — heatmap.js 无官方类型，类型声明见 ./heatmap.d.ts
import h337 from 'heatmap.js';
import type { HeatmapInstance, HeatmapData } from 'heatmap.js';
import {
  sessionReplayApi,
  type HeatmapQueryParams,
  type HeatmapQueryResult,
} from '@/services/sessionReplay';

/** 事件类型选项 */
const EVENT_TYPE_OPTIONS = [
  { label: '点击 (click)', value: 'click' },
  { label: '鼠标移动 (move)', value: 'move' },
];

/** 视口分桶选项 */
const VIEWPORT_BUCKET_OPTIONS: { label: string; value: 'lg' | 'md' | 'sm' }[] = [
  { label: '大屏 (lg ≥ 1200px)', value: 'lg' },
  { label: '中屏 (md 768~1199px)', value: 'md' },
  { label: '小屏 (sm < 768px)', value: 'sm' },
];

/** 天数选项 */
const DAYS_OPTIONS = [
  { label: '近 7 天', value: 7 },
  { label: '近 30 天', value: 30 },
  { label: '近 90 天', value: 90 },
];

/** 预置常用 admin 页面路径（与运营实际高频访问页面对应） */
const PRESET_PAGE_PATHS = [
  { label: '仪表盘', value: '/dashboard' },
  { label: '患者管理', value: '/patient' },
  { label: '预约管理', value: '/appointment' },
  { label: '排班管理', value: '/schedule' },
  { label: '医生管理', value: '/doctor' },
  { label: '会话回放', value: '/session-replay' },
];

/**
 * 各视口桶对应的代表性 admin 画布尺寸。
 * 用于把后端的归一化坐标 (xRatio, yRatio ∈ [0,1]) 还原为像素坐标。
 * 注意：这是「代表性」尺寸，不等于每个用户真实视口；
 * 同一桶内用户的实际尺寸会略有差异，渲染近似即可。
 */
const VIEWPORT_SIZE: Record<'lg' | 'md' | 'sm', { width: number; height: number }> = {
  lg: { width: 1440, height: 900 },
  md: { width: 1024, height: 768 },
  sm: { width: 375, height: 900 },
};

/** 根据本机视口宽度推断默认视口分桶 */
const inferDefaultBucket = (): 'lg' | 'md' | 'sm' => {
  // SSR 兜底（理论上 admin 端不会 SSR，保险起见）
  const w = typeof window !== 'undefined' ? window.innerWidth : 1440;
  if (w >= 1200) return 'lg';
  if (w >= 768) return 'md';
  return 'sm';
};

type LoadState = 'idle' | 'loading' | 'success' | 'empty' | 'error';

const HeatmapPage: React.FC = () => {
  // ===== 筛选项 =====
  const [pagePath, setPagePath] = useState<string>(PRESET_PAGE_PATHS[0].value);
  const [eventType, setEventType] = useState<'click' | 'move'>('click');
  const [viewportBucket, setViewportBucket] = useState<'lg' | 'md' | 'sm'>(inferDefaultBucket());
  const [days, setDays] = useState<number>(30);

  // ===== 数据 / 状态 =====
  const [state, setState] = useState<LoadState>('idle');
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [result, setResult] = useState<HeatmapQueryResult | null>(null);

  // ===== heatmap.js 实例与容器 =====
  const containerRef = useRef<HTMLDivElement>(null);
  const heatmapRef = useRef<HeatmapInstance | null>(null);

  /** 当前视口桶对应的画布尺寸 */
  const canvasSize = useMemo(() => VIEWPORT_SIZE[viewportBucket], [viewportBucket]);

  /**
   * 把后端归一化坐标映射为 heatmap.js 像素数据。
   * value 用 weight；若所有点 weight 相等，heatmap.js 仍能正常渲染
   * （内部按 max/min 插值，单值时为均匀色）。
   */
  const buildHeatmapData = useCallback(
    (res: HeatmapQueryResult): HeatmapData => {
      const { width, height } = VIEWPORT_SIZE[
        (res.viewportBucket as 'lg' | 'md' | 'sm') || viewportBucket
      ];
      const points = res.points || [];
      let max = -Infinity;
      const data = points.map((p) => {
        const v = Number.isFinite(p.weight) ? p.weight : 1;
        if (v > max) max = v;
        return {
          x: Math.round(p.xRatio * width),
          y: Math.round(p.yRatio * height),
          value: v,
        };
      });
      return {
        max: Number.isFinite(max) && max > 0 ? max : 1,
        min: 0,
        data,
      };
    },
    [viewportBucket],
  );

  /** 创建 heatmap.js 实例（仅在 canvasSize 变化或首次挂载时重建） */
  useEffect(() => {
    if (!containerRef.current) return;
    const instance = h337.create({
      container: containerRef.current,
      radius: 40,
      maxOpacity: 0.8,
      minOpacity: 0,
      blur: 0.75,
    });
    heatmapRef.current = instance;
    return () => {
      // 卸载或重建前销毁旧实例，避免 canvas 叠加泄漏
      try {
        instance.destroy();
      } catch {
        /* noop */
      }
      heatmapRef.current = null;
    };
  }, [canvasSize]);

  /** 拉取数据并喂数给 heatmap 实例 */
  const fetchHeatmap = useCallback(async () => {
    if (!pagePath) {
      message.warning('请选择或输入页面路径');
      return;
    }
    const params: HeatmapQueryParams = {
      pagePath,
      eventType,
      viewportBucket,
      days,
    };
    setState('loading');
    setErrorMsg('');
    try {
      const res = await sessionReplayApi.getHeatmap(params);
      const points = res?.points || [];
      setResult(res);

      if (points.length === 0) {
        setState('empty');
        // 清空旧画面
        heatmapRef.current?.setData({ max: 1, min: 0, data: [] });
        return;
      }

      heatmapRef.current?.setData(buildHeatmapData(res));
      setState('success');
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : '热力图数据加载失败，请稍后重试';
      setErrorMsg(msg);
      setState('error');
    }
  }, [pagePath, eventType, viewportBucket, days, buildHeatmapData]);

  // 首次挂载自动加载一次
  useEffect(() => {
    fetchHeatmap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** 画布区域（按当前视口桶尺寸渲染，超大时容器横向滚动） */
  const renderCanvas = () => {
    const { width, height } = canvasSize;
    return (
      <div
        style={{
          overflow: 'auto',
          background: 'var(--color-bg-container)',
          border: '1px solid var(--color-border-secondary)',
          borderRadius: 8,
          padding: 16,
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        {/* heatmap.js canvas 容器；空白底色 + 网格便于直观看到画布范围 */}
        <div
          ref={containerRef}
          style={{
            width,
            height,
            background:
              'repeating-linear-gradient(0deg, var(--color-white), var(--color-white) 39px, var(--color-bg-layout) 40px),' +
              'repeating-linear-gradient(90deg, var(--color-white), var(--color-white) 39px, var(--color-bg-layout) 40px)',
            backgroundColor: 'var(--color-white)',
            border: '1px dashed var(--color-border)',
            position: 'relative',
          }}
        />
      </div>
    );
  };

  /** 内容区按状态切换 */
  const renderBody = () => {
    if (state === 'loading') {
      return (
        <div style={{ textAlign: 'center', padding: '80px 0' }}>
          <Spin size="large" tip="正在加载热力图数据..." />
        </div>
      );
    }
    if (state === 'error') {
      return (
        <Result
          status="error"
          title="热力图加载失败"
          subTitle={errorMsg}
          extra={null}
        />
      );
    }
    if (state === 'empty') {
      return (
        <Empty
          description="当前筛选条件下暂无热力图数据"
          style={{ padding: '80px 0' }}
        />
      );
    }
    // success / idle：渲染 canvas（idle 时画布为空，等待用户查询）
    return renderCanvas();
  };

  return (
    <PageContainer
      header={{
        title: '热力图',
        breadcrumb: {},
      }}
    >
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="行为热力图"
        description={
          <Typography.Paragraph style={{ marginBottom: 0 }}>
            按「页面 × 事件类型 × 视口分桶 × 时间窗」聚合用户点击/移动坐标，归一化后渲染为热力图。
            v1 在空白画布渲染；未来增强可叠加真实页面截图作背景，定位精度更高。
          </Typography.Paragraph>
        }
      />

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap size="middle" align="center">
          <Space.Compact>
            <span style={{ alignSelf: 'center', marginRight: 8 }}>页面路径</span>
            <Select
              showSearch
              style={{ width: 220 }}
              value={pagePath}
              onChange={setPagePath}
              options={PRESET_PAGE_PATHS}
              placeholder="选择或输入页面路径"
              // 允许自定义输入路径（Select 不原生支持自由输入，配合下方 Input 兜底）
              optionFilterProp="label"
            />
          </Space.Compact>
          {/* 自定义路径输入（可选，回车提交） */}
          <Input
            style={{ width: 220 }}
            placeholder="或输入自定义路径，回车确认"
            onPressEnter={(e) => {
              const v = (e.target as HTMLInputElement).value.trim();
              if (v) {
                setPagePath(v);
              }
            }}
            allowClear
          />

          <Space.Compact>
            <span style={{ alignSelf: 'center', marginRight: 8 }}>事件类型</span>
            <Select
              style={{ width: 160 }}
              value={eventType}
              onChange={(v) => setEventType(v as 'click' | 'move')}
              options={EVENT_TYPE_OPTIONS}
            />
          </Space.Compact>

          <Space.Compact>
            <span style={{ alignSelf: 'center', marginRight: 8 }}>视口分桶</span>
            <Select
              style={{ width: 180 }}
              value={viewportBucket}
              onChange={(v) => setViewportBucket(v as 'lg' | 'md' | 'sm')}
              options={VIEWPORT_BUCKET_OPTIONS}
            />
          </Space.Compact>

          <Space.Compact>
            <span style={{ alignSelf: 'center', marginRight: 8 }}>时间窗</span>
            <Select
              style={{ width: 120 }}
              value={days}
              onChange={(v) => setDays(v as number)}
              options={DAYS_OPTIONS}
            />
          </Space.Compact>
        </Space>
      </Card>

      <Card
        size="small"
        title={
          <Space size="small" wrap>
            <span>渲染区</span>
            {result ? (
              <>
                <Tag color="blue">{result.pagePath}</Tag>
                <Tag color="geekblue">{result.eventType}</Tag>
                {result.viewportBucket ? (
                  <Tag color="purple">
                    {result.viewportBucket}（{canvasSize.width}×{canvasSize.height}）
                  </Tag>
                ) : null}
                <Tag color="green">{(result.points || []).length} 个点</Tag>
              </>
            ) : null}
          </Space>
        }
        extra={
          <a
            onClick={(e) => {
              e.preventDefault();
              fetchHeatmap();
            }}
          >
            刷新
          </a>
        }
      >
        {renderBody()}
      </Card>
    </PageContainer>
  );
};

export default HeatmapPage;
