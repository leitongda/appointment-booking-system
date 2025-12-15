/**
 * 修复 macOS 上 os.networkInterfaces() 调用失败的问题
 * 这个问题通常发生在 VPN 或某些网络配置下
 */
const os = require('os');

const originalNetworkInterfaces = os.networkInterfaces;

os.networkInterfaces = function() {
  try {
    return originalNetworkInterfaces.call(os);
  } catch (err) {
    // 返回空对象而不是抛出错误
    console.warn('[fix-network] os.networkInterfaces() failed, returning empty object');
    return {};
  }
};

