/**
 * LiveRegion — 全局 aria-live 播报区域
 *
 * 视觉隐藏（sr-only），供屏幕阅读器读取 Toast 等操作反馈。
 * 使用方式: 在 Layout 层引入 <LiveRegion />，在需要播报处调用 announce()。
 */

let announceFn: (msg: string) => void = () => {};

/** 向屏幕阅读器播报一条消息 */
export const announce = (msg: string) => {
  announceFn(msg);
};

export const LiveRegion: React.FC = () => {
  // 使用 React 状态确保 DOM 更新能触发屏幕阅读器播报
  // 但为了避免引入 React import 开销，这里用原生 DOM 方案
  return (
    <div
      id="a11y-live-region"
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"
    />
  );
};

// 初始化：挂载后 announce 通过 DOM 直接操作
if (typeof window !== 'undefined') {
  announceFn = (msg: string) => {
    const el = document.getElementById('a11y-live-region');
    if (el) {
      // 先清空再赋值，确保相同内容也能重复播报
      el.textContent = '';
      // 使用 requestAnimationFrame 保证清空和赋值不在同一帧
      requestAnimationFrame(() => {
        el.textContent = msg;
      });
    }
  };
}

export default LiveRegion;
