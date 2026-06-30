export default {
  pages: [
    'pages/home/index',
    'pages/scan/index',
    'pages/profile/index'
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#fff',
    navigationBarTitleText: '医疗挂号',
    navigationBarTextStyle: 'black',
    backgroundColor: '#f5f5f5'
  },
  permission: {
    'scope.userLocation': {
      desc: '您的位置信息将用于获取附近的医院'
    }
  }
};
