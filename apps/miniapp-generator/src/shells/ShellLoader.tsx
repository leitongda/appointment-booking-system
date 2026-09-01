import { ComponentType, useState, useEffect } from 'react';
import { View, Text } from '@tarojs/components';

type ShellModule = Record<string, unknown> & {
  default?: ComponentType<any>;
};

interface ShellLoaderProps {
  loader: () => Promise<ShellModule>;
  fallback?: React.ReactNode;
}

export function resolveShellModule(module: ShellModule): ComponentType<any> {
  if (module.default) return module.default;

  const component = Object.values(module).find((value) => typeof value === 'function');
  if (component) return component as ComponentType<any>;

  throw new Error('Shell module does not export a component');
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
        setShell(() => resolveShellModule(module));
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
  importFn: () => Promise<ShellModule>
) {
  return importFn;
}
