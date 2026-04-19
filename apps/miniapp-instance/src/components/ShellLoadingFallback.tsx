import { View } from '@tarojs/components';
import { useTemplate } from '../contexts/TemplateContext';
import './ShellLoadingFallback.less';

export function ShellLoadingFallback() {
  const { template } = useTemplate();
  const primaryColor = template.designTokens.primary;

  return (
    <View className="shell-loading-fallback">
      <View className="shell-loading-spinner" style={{ borderColor: `${primaryColor}20`, borderTopColor: primaryColor }} />
      <View className="shell-loading-text" style={{ color: primaryColor }}>加载中...</View>
    </View>
  );
}
