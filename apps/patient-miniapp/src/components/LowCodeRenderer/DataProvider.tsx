/**
 * 低代码页面数据上下文 Provider
 *
 * 包裹低代码页面根组件，为所有子组件提供统一的数据读写能力。
 *
 * 用法：
 * ```tsx
 * <DataProvider
 *   dataSources={pageSchema.dataSources}
 *   stateSchema={pageSchema.state}
 *   pageParams={{ id: '123' }}
 * >
 *   <LowCodeRenderer schema={pageSchema} />
 * </DataProvider>
 * ```
 *
 * 子组件中消费：
 * ```tsx
 * const { state, setData, getData, fetchDataSource, evaluate } = useLowCodeData();
 * ```
 */

import React, { createContext, useContext, type ReactNode } from 'react';
import type { PageDataSource } from '@hospital/shared';
import { useDataManager, type StateMap, type DataSourceMap } from './data-manager';

// ---------------------------------------------------------------------------
// Context type
// ---------------------------------------------------------------------------

export interface LowCodeDataContextValue {
  /** 页面可变状态 */
  state: StateMap;
  /** 所有数据源的运行时结果 */
  dataSources: DataSourceMap;
  /** 设置页面状态字段 */
  setData: (key: string, value: any) => void;
  /** 按路径读取数据，支持 "state.xxx" / "api.xxx.data" */
  getData: (path: string) => any;
  /** 手动触发指定数据源请求 */
  fetchDataSource: (dataSourceId: string) => Promise<void>;
  /** 对绑定表达式求值，支持 "{{state.xxx}}" / "{{api.xxx.data}}" */
  evaluate: (expression: string) => any;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const LowCodeDataContext = createContext<LowCodeDataContextValue | null>(null);

LowCodeDataContext.displayName = 'LowCodeDataContext';

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export interface DataProviderProps {
  /** 页面 API 数据源定义列表 */
  dataSources: PageDataSource[];
  /** 页面初始状态 schema（key -> defaultValue） */
  stateSchema?: Record<string, any>;
  /** 页面级参数（路由 query 等），会合并到数据源请求参数中 */
  pageParams?: Record<string, any>;
  children: ReactNode;
}

export const DataProvider: React.FC<DataProviderProps> = ({
  dataSources,
  stateSchema,
  pageParams,
  children,
}) => {
  const manager = useDataManager(dataSources, stateSchema, pageParams);

  return (
    <LowCodeDataContext.Provider value={manager}>
      {children}
    </LowCodeDataContext.Provider>
  );
};

// ---------------------------------------------------------------------------
// Consumer hook
// ---------------------------------------------------------------------------

/**
 * 在低代码组件子树中获取数据管理上下文。
 *
 * 必须在 <DataProvider> 内部调用，否则抛出异常。
 */
export function useLowCodeData(): LowCodeDataContextValue {
  const ctx = useContext(LowCodeDataContext);
  if (!ctx) {
    throw new Error('useLowCodeData 必须在 <DataProvider> 内部使用');
  }
  return ctx;
}

export default DataProvider;
