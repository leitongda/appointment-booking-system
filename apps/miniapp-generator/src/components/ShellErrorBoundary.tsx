import { Component, ComponentType, ReactNode } from 'react';
import { View, Button, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useTemplate } from '../contexts/TemplateContext';
import { CloseCircleIcon } from './Icons';
import './ShellErrorBoundary.less';

interface Props {
  children: ReactNode;
  pageName?: string;
}

interface State {
  hasError: boolean;
  error?: Error;
}

/**
 * Shell 组件错误边界
 * 捕获 Shell 渲染错误，显示降级 UI 和重试选项
 */
export class ShellErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    const { pageName = '未知页面' } = this.props;
    console.error(`[ShellErrorBoundary] ${pageName} 渲染错误:`, error);
    console.error('错误堆栈:', errorInfo.componentStack);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined });
  };

  handleBackToHome = () => {
    Taro.switchTab({ url: '/pages/index/index' }).catch(() => {
      Taro.reLaunch({ url: '/pages/index/index' });
    });
  };

  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} onRetry={this.handleRetry} onBackToHome={this.handleBackToHome} />;
    }

    return this.props.children;
  }
}

function ErrorFallback({ error, onRetry, onBackToHome }: { error?: Error; onRetry: () => void; onBackToHome: () => void }) {
  const { template } = useTemplate();
  const primaryColor = template.designTokens.primary;

  return (
    <View className="shell-error-fallback">
      <View className="shell-error-icon">
        <CloseCircleIcon size={56} color={primaryColor} />
      </View>
      <View className="shell-error-title" style={{ color: primaryColor }}>
        页面加载出现问题
      </View>
      <View className="shell-error-desc">
        {error?.message || '页面组件加载失败，请稍后重试'}
      </View>
      <View className="shell-error-actions">
        <Button
          className="shell-error-retry-btn"
          style={{ backgroundColor: primaryColor }}
          onClick={onRetry}
        >
          重新加载
        </Button>
        <Button
          className="shell-error-back-btn"
          onClick={onBackToHome}
        >
          返回首页
        </Button>
      </View>
    </View>
  );
}
