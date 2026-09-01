module.exports = {
  presets: [
    ['taro', {
      framework: 'react',
      ts: true,
    }],
  ],
  plugins: [
    ['import', {
      libraryName: '@nutui/nutui-react-taro',
      libraryDirectory: 'dist/es/packages',
      style: true,
      camel2DashComponentName: false,
    }, '@nutui/nutui-react-taro'],
  ],
};
