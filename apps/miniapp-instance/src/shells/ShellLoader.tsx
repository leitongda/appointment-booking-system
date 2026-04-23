import { ComponentType, useState, useEffect } from 'react';
import { View, Text } from '@tarojs/components';

interface ShellLoaderProps {
  loader: () => Promise<{ default: ComponentType<any> }>;
  fallback?: React.ReactNode;
}

/**
 * Shell 动态加载器
 * 用于懒加载非首页 Shell，减少主包体积
 */
export function ShellLoader({ loader, fallback }: ShellLoaderProps) {
  const [Shell, setShell] = useState<ComponentType<any> | null>(null);

  useEffect(() => {
    let mounted = true;
    loader().then(module => {
      if (mounted) {
        setShell(() => module.default);
      }
    }).catch(error => {
      console.error('[ShellLoader] 加载失败:', error);
    });
    return () => {
      mounted = false;
    };
  }, [loader]);

  if (!Shell) {
    return fallback || (
      <View style={{ padding: '64rpx', textAlign: 'center' }}>
        <Text style={{ fontSize: '28rpx', color: '#9CA3AF' }}>加载中...</Text>
      </View>
    );
  }

  return <Shell />;
}

/**
 * 创建 Shell 动态导入函数
 * @param path Shell 相对于 shells 目录的路径
 * @example
 * const loadHomeStandard = createShellLoader(() => import('./home/HomeStandard'));
 * <ShellLoader loader={loadHomeStandard} />
 */
export function createShellLoader(
  importFn: () => Promise<{ default: ComponentType<any> }>
) {
  return importFn;
}
