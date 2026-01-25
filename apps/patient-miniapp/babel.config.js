module.exports = {
  presets: [
    ['taro', {
      framework: 'react',
      ts: true,
    }],
  ],
  plugins: [
    // NutUI 样式按需加载
    // 自动将 import { Button } from '@nutui/nutui-react-taro'
    // 转换为同时导入对应的样式文件
    ['import', {
      libraryName: '@nutui/nutui-react-taro',
      libraryDirectory: 'dist/es/packages',
      style: true,
      camel2DashComponentName: false,
    }, '@nutui/nutui-react-taro'],
  ],
};

