import { JSEncrypt } from 'jsencrypt';

// 缓存公钥 - 同时支持内存和 localStorage
let cachedPublicKey: string | null = null;
const PUBLIC_KEY_STORAGE_KEY = 'rsa_public_key';
const PUBLIC_KEY_TIMESTAMP_KEY = 'rsa_public_key_timestamp';
const PUBLIC_KEY_CACHE_DURATION = 24 * 60 * 60 * 1000; // 24小时

/**
 * 从 localStorage 加载公钥
 */
const loadPublicKeyFromStorage = (): string | null => {
  try {
    const timestamp = localStorage.getItem(PUBLIC_KEY_TIMESTAMP_KEY);
    const now = Date.now();
    
    // 检查是否过期
    if (timestamp && (now - parseInt(timestamp)) < PUBLIC_KEY_CACHE_DURATION) {
      return localStorage.getItem(PUBLIC_KEY_STORAGE_KEY);
    }
    
    // 过期则清除
    localStorage.removeItem(PUBLIC_KEY_STORAGE_KEY);
    localStorage.removeItem(PUBLIC_KEY_TIMESTAMP_KEY);
    return null;
  } catch (error) {
    console.warn('加载公钥缓存失败:', error);
    return null;
  }
};

/**
 * 设置 RSA 公钥（同时缓存到内存和 localStorage）
 */
export const setPublicKey = (publicKey: string): void => {
  cachedPublicKey = publicKey;
  
  try {
    localStorage.setItem(PUBLIC_KEY_STORAGE_KEY, publicKey);
    localStorage.setItem(PUBLIC_KEY_TIMESTAMP_KEY, Date.now().toString());
    console.log('✓ RSA 公钥已缓存');
  } catch (error) {
    console.warn('保存公钥缓存失败:', error);
  }
};

/**
 * 获取缓存的公钥（优先从内存，其次从 localStorage）
 */
export const getPublicKey = (): string | null => {
  // 优先返回内存缓存
  if (cachedPublicKey) {
    return cachedPublicKey;
  }
  
  // 尝试从 localStorage 加载
  const storedKey = loadPublicKeyFromStorage();
  if (storedKey) {
    cachedPublicKey = storedKey;
    console.log('✓ 从缓存加载 RSA 公钥');
    return storedKey;
  }
  
  return null;
};

/**
 * 清除缓存的公钥（同时清除内存和 localStorage）
 */
export const clearPublicKey = (): void => {
  cachedPublicKey = null;
  
  try {
    localStorage.removeItem(PUBLIC_KEY_STORAGE_KEY);
    localStorage.removeItem(PUBLIC_KEY_TIMESTAMP_KEY);
    console.log('✓ RSA 公钥缓存已清除');
  } catch (error) {
    console.warn('清除公钥缓存失败:', error);
  }
};

/**
 * RSA 加密
 * @param plainText 明文
 * @param publicKey 可选，如果不传则使用缓存的公钥
 * @returns Base64 编码的加密数据
 */
export const rsaEncrypt = (plainText: string, publicKey?: string): string => {
  const key = publicKey || cachedPublicKey;
  
  if (!key) {
    throw new Error('RSA 公钥未设置');
  }
  
  const encrypt = new JSEncrypt();
  encrypt.setPublicKey(key);
  
  const encrypted = encrypt.encrypt(plainText);
  
  if (!encrypted) {
    throw new Error('RSA 加密失败');
  }
  
  return encrypted;
};

export const cryptoUtils = {
  setPublicKey,
  getPublicKey,
  clearPublicKey,
  rsaEncrypt,
};

