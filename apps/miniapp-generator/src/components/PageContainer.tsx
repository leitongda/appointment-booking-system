import { PropsWithChildren } from 'react';
import { View } from '@tarojs/components';
import { useTemplate } from '../contexts/TemplateContext';

interface PageContainerProps {
  className?: string;
  style?: React.CSSProperties;
  showPadding?: boolean;
}

export function PageContainer({ children, className, style, showPadding = true }: PropsWithChildren<PageContainerProps>) {
  const { tokens } = useTemplate();

  return (
    <View
      className={className}
      style={{
        minHeight: '100vh',
        backgroundColor: '#F5F5F5',
        padding: showPadding ? '0 0 calc(env(safe-area-inset-bottom) + 120rpx)' : '0',
        ...style,
        '--theme-primary': tokens.primary,
        '--theme-primary-soft': tokens.primarySoft,
        '--theme-accent': tokens.accent,
      } as React.CSSProperties}
    >
      {children}
    </View>
  );
}
