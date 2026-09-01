import { View, Text } from '@tarojs/components';
import { useTemplate } from '../contexts/TemplateContext';

export function EmptyPlaceholder({ pageName }: { pageName: string }) {
  const { tone } = useTemplate();

  return (
    <View style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '120rpx 40rpx',
    }}>
      <Text style={{ color: '#9CA3AF', fontSize: '28rpx' }}>
        {pageName} — 待实现
      </Text>
      <Text style={{ color: '#D1D5DB', fontSize: '24rpx', marginTop: '16rpx' }}>
        模板: {tone.bookingLabel}
      </Text>
    </View>
  );
}
