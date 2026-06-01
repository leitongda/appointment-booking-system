/**
 * 空模块 - 用于在小程序环境中替代不支持的库
 *
 * 小程序环境没有 Web Crypto API (globalThis.crypto)，
 * jsencrypt 库在加载时会访问该 API 导致错误。
 * 由于小程序端不需要 RSA 加密功能（管理员登录使用），
 * 我们用这个空模块替代 jsencrypt。
 */

// JSEncrypt 的空实现
class JSEncrypt {
  setPublicKey(_key: string): void {
    console.warn('[小程序] JSEncrypt 在小程序环境中不可用');
  }

  setPrivateKey(_key: string): void {
    console.warn('[小程序] JSEncrypt 在小程序环境中不可用');
  }

  encrypt(_text: string): string | false {
    console.warn('[小程序] JSEncrypt.encrypt 在小程序环境中不可用');
    return false;
  }

  decrypt(_text: string): string | false {
    console.warn('[小程序] JSEncrypt.decrypt 在小程序环境中不可用');
    return false;
  }
}

export default JSEncrypt;
export { JSEncrypt };
