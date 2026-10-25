/**
 * useGuidedTour - 操作指引核心 Hook
 *
 * 职责：
 * 1. 加载已发布指引列表 + 用户进度
 * 2. 根据当前路由匹配对应的步骤
 * 3. 管理 open/current 受控状态
 * 4. 步骤切换时持久化进度
 * 5. 路由变化时自动恢复步骤
 * 6. 跨路由引导：步骤 route !== 当前路由时自动 navigate
 */
import {useCallback, useEffect, useRef, useState} from 'react';
import {history, useLocation} from '@umijs/max';
import {guideToursApi, type GuideTourItem} from '@hospital/api';
import type { TourProps } from 'antd';
import {t} from '@/utils/locale';

export interface UseGuidedTourOptions {
  /** 指定指引 code，不传则加载全部 */
  tourCode?: string;
  /** 自动触发：首次访问时自动开始 */
  autoTrigger?: boolean;
}

export interface GuidedTourState {
  /** 是否显示 Tour */
  open: boolean;
  /** 当前步骤索引 */
  current: number;
  /** 当前指引的步骤列表（转换为 antd Tour 可消费的结构） */
  steps: NonNullable<TourProps['steps']>;
  /** 当前指引完整信息 */
  activeTour: GuideTourItem | null;
  /** 所有可用指引 */
  tours: GuideTourItem[];
  /** 加载中 */
  loading: boolean;
  /** 开始指定指引 */
  startTour: (tourId: string) => void;
  /** 步骤切换回调 */
  onChange: (step: number) => void;
  /** Tour 关闭回调 */
  onClose: () => void;
  /** Tour 完成回调 */
  onFinish: () => void;
}

const PROGRESS_DEBOUNCE_MS = 500;

export function useGuidedTour(options: UseGuidedTourOptions = {}): GuidedTourState {
  const { tourCode, autoTrigger = false } = options;
  const location = useLocation();

  const [tours, setTours] = useState<GuideTourItem[]>([]);
  const [activeTour, setActiveTour] = useState<GuideTourItem | null>(null);
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState(0);
  const [loading, setLoading] = useState(true);

  // 防止重复触发
  const autoTriggeredRef = useRef(false);
  // 防抖定时器
  const progressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ==================== 加载指引列表 ====================

  const fetchTours = useCallback(async () => {
    try {
      setLoading(true);
      const items = await guideToursApi.getActive();
      setTours(items || []);

      // 如果指定了 tourCode，自动匹配
      if (tourCode) {
        const matched = items.find((t) => t.code === tourCode);
        if (matched && matched.progressStatus !== 1) {
          setActiveTour(matched);
          setCurrent(matched.currentStep);
          setOpen(true);
        }
      }
    } catch (e) {
      console.error('[GuidedTour] 加载指引失败:', e);
    } finally {
      setLoading(false);
    }
  }, [tourCode]);

  useEffect(() => {
    fetchTours();
  }, [fetchTours]);

  // ==================== 自动触发 ====================

  useEffect(() => {
    if (!autoTrigger || autoTriggeredRef.current || loading || tours.length === 0) return;

    // 检查是否首次访问（localStorage）
    const triggered = localStorage.getItem('guide_tour_auto_triggered');
    if (triggered) return;

    // 找到第一个未完成的指引
    const pending = tours.find((t) => t.progressStatus !== 1);
    if (pending) {
      setActiveTour(pending);
      setCurrent(pending.currentStep);
      setOpen(true);
      autoTriggeredRef.current = true;
      localStorage.setItem('guide_tour_auto_triggered', '1');
    }
  }, [autoTrigger, loading, tours]);

  // ==================== URL 参数触发 ====================

  useEffect(() => {
    if (loading || tours.length === 0) return;

    const params = new URLSearchParams(location.search);
    const guideCode = params.get('guide');
    if (!guideCode) return;

    const matched = tours.find((t) => t.code === guideCode);
    if (matched) {
      setActiveTour(matched);
      setCurrent(matched.currentStep);
      setOpen(true);
      // 清除 URL 参数，避免刷新时重复触发
      params.delete('guide');
      const newSearch = params.toString();
      const newPath = location.pathname + (newSearch ? `?${newSearch}` : '') + (location.hash || '');
      window.history.replaceState({}, '', newPath);
    }
  }, [loading, tours, location.search]);

  // ==================== 跨路由步骤匹配 ====================

  // 当前路由
  const currentRoute = location.pathname;

  // 计算当前指引中属于当前路由的步骤
  const currentSteps = activeTour?.steps || [];

  // 查找当前步骤应该在的路由
  const targetRoute = currentSteps[current]?.route;

  // 如果当前步骤的路由不是当前路由，自动跳转
  useEffect(() => {
    if (!open || !activeTour || !targetRoute) return;

    // 去掉 hash 路由的 # 前缀进行比较
    const normalizedCurrent = currentRoute.replace(/^\/#/, '');
    const normalizedTarget = targetRoute.replace(/^\/#/, '');

    if (normalizedCurrent !== normalizedTarget) {
      // 延迟跳转，避免在渲染过程中触发
      const timer = setTimeout(() => {
        history.push(targetRoute);
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [open, activeTour, targetRoute, currentRoute]);

  // ==================== 进度持久化 ====================

  const persistProgress = useCallback(
    (step: number, status?: number) => {
      if (!activeTour) return;

      // 防抖：避免快速切换时频繁请求
      if (progressTimerRef.current) {
        clearTimeout(progressTimerRef.current);
      }

      progressTimerRef.current = setTimeout(async () => {
        try {
          await guideToursApi.updateProgress(activeTour.id, {
            currentStep: step,
            ...(status !== undefined ? { status } : {}),
          });
        } catch (e) {
          console.error('[GuidedTour] 保存进度失败:', e);
        }
      }, PROGRESS_DEBOUNCE_MS);
    },
    [activeTour],
  );

  // 组件卸载时清理定时器
  useEffect(() => {
    return () => {
      if (progressTimerRef.current) {
        clearTimeout(progressTimerRef.current);
      }
    };
  }, []);

  // ==================== 回调 ====================

  const startTour = useCallback(
    (tourId: string) => {
      const tour = tours.find((t) => t.id === tourId);
      if (tour) {
        setActiveTour(tour);
        setCurrent(tour.currentStep);
        setOpen(true);
      }
    },
    [tours],
  );

  const onChange = useCallback(
    (step: number) => {
      setCurrent(step);
      persistProgress(step);
    },
    [persistProgress],
  );

  const onClose = useCallback(() => {
    setOpen(false);
    // 保存当前进度（不改变状态）
    if (activeTour) {
      persistProgress(current);
    }
  }, [activeTour, current, persistProgress]);

  const onFinish = useCallback(() => {
    setOpen(false);
    if (activeTour) {
      persistProgress(current, 1); // status=1 已完成
    }
  }, [activeTour, current, persistProgress]);

  // ==================== 构造 antd Tour steps ====================

  const antdSteps: NonNullable<TourProps['steps']> = currentSteps.map((step) => ({
    title: t(step.title),
    description: t(step.description),
    target: (() => document.querySelector<HTMLElement>(step.target)) as NonNullable<TourProps['steps']>[number]['target'],
    placement: step.placement as NonNullable<TourProps['steps']>[number]['placement'],
  }));

  return {
    open,
    current,
    steps: antdSteps,
    activeTour,
    tours,
    loading,
    startTour,
    onChange,
    onClose,
    onFinish,
  };
}
