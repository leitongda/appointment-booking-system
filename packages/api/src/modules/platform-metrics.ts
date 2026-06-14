import { request } from '../request';

/** 全平台经营总览 */
export interface PlatformOverviewData {
  startDate: string;
  endDate: string;
  tenantCount: number;
  activeStoreCount: number;
  appointmentCount: number;
  visitCount: number;
  completedCount: number;
  noShowCount: number;
  cancelledCount: number;
  newPatientCount: number;
  revenue: number;
  noShowRate: number | null;
}

/** 租户经营对比项 */
export interface TenantCompareItem {
  tenantId: string | null;
  tenantName: string | null;
  storeCount: number;
  appointmentCount: number;
  visitCount: number;
  completedCount: number;
  noShowCount: number;
  newPatientCount: number;
  revenue: number;
  noShowRate: number | null;
}

/** 门店经营对比项 */
export interface StoreCompareItem {
  storeId: string;
  storeName: string | null;
  tenantId: string | null;
  tenantName: string | null;
  appointmentCount: number;
  visitCount: number;
  completedCount: number;
  noShowCount: number;
  newPatientCount: number;
  revenue: number;
  noShowRate: number | null;
}

/** 趋势数据点 */
export interface PlatformTrendPoint {
  date: string;
  appointmentCount: number;
  visitCount: number;
  completedCount: number;
  newPatientCount: number;
  revenue: number;
}

export interface PlatformMetricsQuery {
  startDate?: string;
  endDate?: string;
}

export interface StoreCompareQuery extends PlatformMetricsQuery {
  tenantId?: string;
  sortBy?: 'revenue' | 'appointment' | 'visit' | 'new_patient';
  limit?: number;
}

export const platformMetricsApi = {
  /** 全平台经营总览 */
  getOverview: (params?: PlatformMetricsQuery) =>
    request.get<PlatformOverviewData>('/platform-metrics/overview', { params }),

  /** 租户经营对比 */
  getTenantsCompare: (params?: PlatformMetricsQuery & { sortBy?: string; limit?: number }) =>
    request.get<TenantCompareItem[]>('/platform-metrics/tenants/compare', { params }),

  /** 门店经营对比 */
  getStoresCompare: (params?: StoreCompareQuery) =>
    request.get<StoreCompareItem[]>('/platform-metrics/stores/compare', { params }),

  /** 平台整体趋势 */
  getTrend: (params?: PlatformMetricsQuery) =>
    request.get<PlatformTrendPoint[]>('/platform-metrics/trend', { params }),

  /** 导出门店经营对比明细（Excel blob） */
  exportStoresCompare: (params?: StoreCompareQuery): Promise<Blob> =>
    request.get('/platform-metrics/stores/export', {
      params,
      responseType: 'blob',
    } as any),
};
