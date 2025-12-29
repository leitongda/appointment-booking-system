/**
 * 修复 macOS 上 os.networkInterfaces() 调用失败的问题
 * 这个问题通常发生在 VPN 或某些网络配置下
 */
const os = require('os');
const net = require('net');

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

/**
 * 修复 macOS 上绑定 0.0.0.0 地址权限问题
 * 将 0.0.0.0 强制替换为 127.0.0.1
 */
const originalListen = net.Server.prototype.listen;

net.Server.prototype.listen = function(...args) {
  // 处理不同的参数格式
  if (args.length > 0) {
    const firstArg = args[0];
    
    // 格式: listen(port, host, ...)
    if (typeof firstArg === 'number' && typeof args[1] === 'string') {
      if (args[1] === '0.0.0.0') {
        args[1] = '127.0.0.1';
        console.log('[fix-network] Replaced 0.0.0.0 with 127.0.0.1 for listen');
      }
    }
    
    // 格式: listen(options, ...)
    if (typeof firstArg === 'object' && firstArg !== null) {
      if (firstArg.host === '0.0.0.0') {
        firstArg.host = '127.0.0.1';
        console.log('[fix-network] Replaced 0.0.0.0 with 127.0.0.1 for listen');
      }
    }
  }
  
  return originalListen.apply(this, args);
};

