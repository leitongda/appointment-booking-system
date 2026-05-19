/**
 * 多环境代理装配
 *
 * 通过 `createProxy` 工厂消除 dev/test/pre 三套环境的重复定义。
 *
 * 顺带修复：为 test/pre 补齐 `_AMapService` 代理，与 dev 对齐避免环境间行为漂移。
 *
 * @doc https://umijs.org/docs/guides/proxy
 */
import { PROXY_TARGET } from '../constants/env';
import { createProxy } from './createProxy';
import { AMAP_PATH, API_PATH, UPLOADS_PATH } from './rules';

const dev = {
  [API_PATH]: createProxy(PROXY_TARGET, { rewriteApi: true, secure: false }),
  [UPLOADS_PATH]: createProxy(PROXY_TARGET, { secure: false }),
  [AMAP_PATH]: createProxy(PROXY_TARGET, { secure: false }),
};

const test = {
  [API_PATH]: createProxy(PROXY_TARGET, { rewriteApi: true }),
  [UPLOADS_PATH]: createProxy(PROXY_TARGET),
  [AMAP_PATH]: createProxy(PROXY_TARGET),
};

const pre = {
  [API_PATH]: createProxy(PROXY_TARGET, { rewriteApi: true }),
  [UPLOADS_PATH]: createProxy(PROXY_TARGET),
  [AMAP_PATH]: createProxy(PROXY_TARGET),
};

const proxy = { dev, test, pre };

export default proxy;
