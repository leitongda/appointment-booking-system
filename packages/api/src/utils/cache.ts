/**
 * 通用 TTL 请求缓存工具
 *
 * 提供模块级的带过期时间的内存缓存,并对同一 key 的并发请求做去重(inflight 共享 Promise),
 * 避免短时间内多个调用点重复发起相同的 GET 请求。
 *
 * 设计参考:
 * - crypto.ts 的双层 TTL 缓存风格
 * - useDict.ts 的 SWR(stale-while-revalidate)思路
 *
 * 适用场景:变更不频繁、可容忍短时间脏读的只读列表型接口,例如操作指引、字典、概览等。
 */

interface CacheEntry<T> {
  data: T;
  expireAt: number;
}

export interface TTLCacheOptions {
  /** 缓存有效期(毫秒) */
  ttl: number;
}

export interface TTLCache<T> {
  /** 同步读取缓存(不触发请求),未命中或已过期返回 undefined */
  get(key: string): T | undefined;
  /** 手动写入缓存(刷新过期时间) */
  set(key: string, data: T): void;
  /**
   * 命中未过期缓存则直接返回;否则执行 fetcher。
   * 同一 key 的并发调用共享同一个 inflight Promise,只发一次请求。
   * 仅当 fetcher 成功时才回写缓存,失败不缓存。
   */
  getOrFetch(key: string, fetcher: () => Promise<T>): Promise<T>;
  /** 失效指定 key;不传 key 则清空全部缓存 */
  invalidate(key?: string): void;
}

export function createTTLCache<T>(options: TTLCacheOptions): TTLCache<T> {
  const { ttl } = options;
  const cache = new Map<string, CacheEntry<T>>();
  const inflight = new Map<string, Promise<T>>();

  const isExpired = (entry: CacheEntry<T>): boolean => Date.now() > entry.expireAt;

  return {
    get(key: string): T | undefined {
      const entry = cache.get(key);
      if (!entry) return undefined;
      if (isExpired(entry)) {
        cache.delete(key);
        return undefined;
      }
      return entry.data;
    },

    set(key: string, data: T): void {
      cache.set(key, { data, expireAt: Date.now() + ttl });
    },

    getOrFetch(key: string, fetcher: () => Promise<T>): Promise<T> {
      // 1. 命中未过期缓存,直接返回
      const cached = this.get(key);
      if (cached !== undefined) {
        return Promise.resolve(cached);
      }

      // 2. 已有 inflight 请求,复用同一个 Promise(并发去重)
      const existing = inflight.get(key);
      if (existing) {
        return existing;
      }

      // 3. 发起新请求,成功后回写缓存
      const promise = fetcher()
        .then((data) => {
          this.set(key, data);
          return data;
        })
        .finally(() => {
          inflight.delete(key);
        });

      inflight.set(key, promise);
      return promise;
    },

    invalidate(key?: string): void {
      if (key === undefined) {
        cache.clear();
      } else {
        cache.delete(key);
      }
    },
  };
}
