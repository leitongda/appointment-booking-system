import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * 通用倒计时 Hook
 *
 * 提供 `start(seconds)` 启动倒计时，`reset()` 中断并归零。
 * 组件卸载时自动清理定时器，重复 `start` 会先清掉旧定时器避免叠加。
 *
 * @example
 * const { count, running, start, reset } = useCountdown();
 * <Button disabled={running} onClick={() => start(60)}>
 *   {running ? `${count}s` : '获取验证码'}
 * </Button>
 */
export interface UseCountdownResult {
  /** 当前剩余秒数，未运行时为 0 */
  count: number;
  /** 是否正在倒计时 */
  running: boolean;
  /** 启动倒计时 */
  start: (seconds: number) => void;
  /** 立即终止倒计时并归零 */
  reset: () => void;
}

export function useCountdown(): UseCountdownResult {
  const [count, setCount] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    clearTimer();
    setCount(0);
  }, [clearTimer]);

  const start = useCallback(
    (seconds: number) => {
      clearTimer();
      const initial = Math.max(0, Math.floor(seconds));
      setCount(initial);
      if (initial <= 0) return;
      timerRef.current = setInterval(() => {
        setCount((prev) => {
          if (prev <= 1) {
            clearTimer();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    },
    [clearTimer],
  );

  // unmount cleanup
  useEffect(() => {
    return () => clearTimer();
  }, [clearTimer]);

  return { count, running: count > 0, start, reset };
}
