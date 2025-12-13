/**
 * 将 API 响应转换为 ProTable 需要的格式
 * @param res API 返回的数据（数组或分页对象）
 * @returns { data, success, total }
 */
export function toProTableResult<T>(
  res: T[] | { items?: T[]; data?: T[]; total?: number }
) {
  if (Array.isArray(res)) {
    return { data: res, success: true, total: res.length };
  }
  const items = res.items || res.data || [];
  const total = res.total ?? items.length;
  return { data: items, success: true, total };
}

