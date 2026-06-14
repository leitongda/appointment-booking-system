/**
 * GuidedTour - 全局操作指引组件
 *
 * 挂载在 Layout 的 childrenRender 中，全局生效。
 * 使用 antd Tour 组件 + useGuidedTour hook 实现跨路由引导。
 */
import { Tour } from 'antd';
import { useGuidedTour } from '@/hooks/useGuidedTour';

interface GuidedTourProps {
  /** 指定指引 code，不传则等待外部触发 */
  tourCode?: string;
  /** 首次访问自动触发 */
  autoTrigger?: boolean;
}

export default function GuidedTour({ tourCode, autoTrigger = true }: GuidedTourProps) {
  const { open, current, steps, onChange, onClose, onFinish } = useGuidedTour({
    tourCode,
    autoTrigger,
  });

  if (!steps.length) {
    return null;
  }

  return (
    <Tour
      open={open}
      current={current}
      steps={steps}
      onChange={onChange}
      onClose={onClose}
      onFinish={onFinish}
      indicatorsRender={(current, total) => (
        <span style={{ fontSize: 12, color: '#999' }}>
          {current + 1} / {total}
        </span>
      )}
    />
  );
}
