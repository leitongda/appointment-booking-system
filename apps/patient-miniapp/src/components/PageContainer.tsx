/**
 * 页面容器组件
 * 用于包装页面根元素，支持字体模式切换
 */

import { View } from '@tarojs/components';
import { useState, useEffect, PropsWithChildren } from 'react';
import Taro from '@tarojs/taro';
import { STORAGE_KEYS } from '@hospital/shared';
import type { FontMode } from '../utils/fontMode';
import { applyThemeNavigationBar } from '../utils/theme';

interface PageContainerProps extends PropsWithChildren {
  className?: string;
}

/**
 * 页面容器组件
 * 自动应用字体模式样式类
 */
export function PageContainer({ className = '', children }: PageContainerProps) {
  const [fontMode, setFontMode] = useState<FontMode>('standard');

  // 初始化时读取字体模式
  useEffect(() => {
    try {
      const savedMode = Taro.getStorageSync(STORAGE_KEYS.FONT_MODE) as FontMode;
      if (savedMode === 'standard' || savedMode === 'elder') {
        setFontMode(savedMode);
      }
    } catch (error) {
      console.error('读取字体模式失败:', error);
    }

    applyThemeNavigationBar();
  }, []);

  // 监听页面显示，重新读取字体模式（用户可能在设置页面切换了模式）
  Taro.useDidShow(() => {
    try {
      const savedMode = Taro.getStorageSync(STORAGE_KEYS.FONT_MODE) as FontMode;
      if (savedMode === 'standard' || savedMode === 'elder') {
        setFontMode(savedMode);
      }
    } catch (error) {
      // 忽略读取错误
    }

    applyThemeNavigationBar();
  });

  const fontModeClass = fontMode === 'elder' ? 'font-mode-elder' : '';

  return (
    <View className={`${className} ${fontModeClass}`.trim()}>
      {children}
    </View>
  );
}

export default PageContainer;
