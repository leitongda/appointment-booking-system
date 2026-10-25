import { View, Text, Button, Image } from '@tarojs/components';
import type { ReactNode } from 'react';
import { useTemplate } from '../contexts/TemplateContext';
import { useThemePrimaryColor } from '../utils/theme';
import { FileIcon, CloseCircleIcon, ClockIcon, CalendarIcon, HospitalIcon, DoctorIcon } from './Icons';
import './EmptyState.less';

interface EmptyStateProps {
  type?: 'empty' | 'error' | 'loading';
  /** 自定义图标节点；缺省按 type 使用内置线性图标 */
  icon?: ReactNode;
  title?: string;
  description?: string;
  buttonText?: string;
  onButtonClick?: () => void;
}

/**
 * 通用空态/错误态组件
 * 使用模板 tone 配置中的文案
 */
export function EmptyState({
  type = 'empty',
  icon,
  title,
  description,
  buttonText,
  onButtonClick,
}: EmptyStateProps) {
  const { template, tone } = useTemplate();
  const primaryColor = useThemePrimaryColor();

  // 默认配置
  const config: Record<NonNullable<EmptyStateProps['type']>, {
    icon: ReactNode;
    title: string;
    description: string;
    buttonText?: string;
  }> = {
    empty: {
      icon: icon || <FileIcon size={56} color={primaryColor} />,
      title: title || '暂无数据',
      description: description || '',
    },
    error: {
      icon: icon || <CloseCircleIcon size={56} color={primaryColor} />,
      title: title || '加载失败',
      description: description || '请稍后重试',
      buttonText: buttonText || '点击重试',
    },
    loading: {
      icon: icon || <ClockIcon size={56} color={primaryColor} />,
      title: title || '加载中...',
      description: description || '',
    },
  };

  const currentConfig = config[type];

  return (
    <View className="empty-state">
      <View className="empty-state-icon">{currentConfig.icon}</View>
      <View className="empty-state-title" style={{ color: primaryColor }}>
        {currentConfig.title}
      </View>
      {currentConfig.description && (
        <View className="empty-state-desc">{currentConfig.description}</View>
      )}
      {type === 'error' && onButtonClick && (
        <Button
          className="empty-state-btn"
          style={{ backgroundColor: primaryColor }}
          onClick={onButtonClick}
        >
          {currentConfig.buttonText}
        </Button>
      )}
    </View>
  );
}

/**
 * 预约空态组件 - 使用模板 emptyBookingText
 */
export function AppointmentEmptyState({ onRetry }: { onRetry?: () => void }) {
  const { tone } = useTemplate();
  return (
    <EmptyState
      type="empty"
      icon={<CalendarIcon size={56} color={useThemePrimaryColor()} />}
      title={tone.emptyBookingText}
      description="点击下方按钮开始预约"
      buttonText="去预约"
      onButtonClick={() => {
        // 跳转到科室页
        onRetry?.();
      }}
    />
  );
}

/**
 * 科室空态组件
 */
export function DepartmentEmptyState() {
  return (
    <EmptyState
      type="empty"
      icon={<HospitalIcon size={56} color={useThemePrimaryColor()} />}
      title="暂无科室信息"
      description="当前医院暂未开设科室"
    />
  );
}

/**
 * 医生空态组件
 */
export function DoctorEmptyState() {
  return (
    <EmptyState
      type="empty"
      icon={<DoctorIcon size={56} color={useThemePrimaryColor()} />}
      title="暂无医生信息"
      description="当前科室暂无医生出诊"
    />
  );
}

/**
 * 加载失败错误态组件
 */
export function LoadFailedErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <EmptyState
      type="error"
      title="加载失败"
      description="数据加载异常，请检查网络后重试"
      buttonText="点击重试"
      onButtonClick={onRetry}
    />
  );
}
