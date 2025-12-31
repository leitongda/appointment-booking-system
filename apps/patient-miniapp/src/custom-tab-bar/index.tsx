import { View, Image, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import './index.less';

// TabBar 配置
// 注意：使用相对路径引用图片资源，避免 base64 编码导致图片显示问题
// 路径相对于小程序根目录（dist 目录）
const tabBarList = [
  {
    pagePath: '/pages/index/index',
    text: '首页',
    iconPath: '/assets/tabbar/home.png',
    selectedIconPath: '/assets/tabbar/home-active.png',
  },
  {
    pagePath: '/pages/appointment/index',
    text: '预约',
    iconPath: '/assets/tabbar/appointment.png',
    selectedIconPath: '/assets/tabbar/appointment-active.png',
  },
  {
    pagePath: '/pages/profile/index',
    text: '我的',
    iconPath: '/assets/tabbar/profile.png',
    selectedIconPath: '/assets/tabbar/profile-active.png',
  },
];

export default function CustomTabBar() {
  const [selected, setSelected] = useState(0);

  useEffect(() => {
    // 监听页面显示，更新选中状态
    const updateSelected = () => {
      const pages = Taro.getCurrentPages();
      if (pages.length > 0) {
        const currentPage = pages[pages.length - 1];
        const currentPath = '/' + currentPage.route;
        const index = tabBarList.findIndex((item) => item.pagePath === currentPath);
        if (index !== -1) {
          setSelected(index);
        }
      }
    };

    updateSelected();
  }, []);

  const handleSwitch = (index: number, pagePath: string) => {
    if (index === selected) return;
    
    setSelected(index);
    Taro.switchTab({
      url: pagePath,
    });
  };

  return (
    <View className="custom-tab-bar">
      {tabBarList.map((item, index) => (
        <View
          key={item.pagePath}
          className="custom-tab-bar__item"
          onClick={() => handleSwitch(index, item.pagePath)}
        >
          <Image
            className="custom-tab-bar__icon"
            src={index === selected ? item.selectedIconPath : item.iconPath}
            mode="aspectFit"
          />
          <Text
            className={`custom-tab-bar__text ${
              index === selected ? 'custom-tab-bar__text--active' : ''
            }`}
          >
            {item.text}
          </Text>
        </View>
      ))}
    </View>
  );
}

