import type { PageResult } from '@hospital/shared';

/**
 * 分页加载全部数据的辅助函数
 * 当 API 的 pageSize 有限制时，通过循环请求获取所有数据
 *
 * @param fetcher - 分页获取数据的函数，接收 page 和 pageSize 参数
 * @param maxPageSize - 单次请求最大页大小，默认 100
 * @returns 包含所有数据的数组
 */
export async function fetchAllData<T>(
  fetcher: (page: number, pageSize: number) => Promise<PageResult<T>>,
  maxPageSize: number = 100,
): Promise<T[]> {
  const allData: T[] = [];
  let page = 1;
  let hasMore = true;

  while (hasMore) {
    const result = await fetcher(page, maxPageSize);
    allData.push(...result.data);
    hasMore = allData.length < result.total;
    page++;
  }

  return allData;
}
