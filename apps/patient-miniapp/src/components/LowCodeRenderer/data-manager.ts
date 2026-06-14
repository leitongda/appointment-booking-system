/**
 * useDataManager -- 低代码运行时页面级数据状态管理 Hook
 *
 * 职责:
 * 1. 管理页面级 state (Record<string, any>), 支持 dot-notation 嵌套路径读写
 * 2. 自动拉取 refresh:'onMount' 的数据源 (manual === false / undefined)
 * 3. 支持手动触发 fetchDataSource(id, params)
 * 4. 暴露 evaluate(expr) 用于表达式求值, 基于 expression-engine
 * 5. 变量作用域: pageParams / apiData / formData / custom
 */

import { useState, useEffect, useRef, useCallback } from '@tarojs/taro';
import Taro from '@tarojs/taro';
import type { ApiDataSource, PageDataSource } from '@hospital/shared';
import type { LinkageRule, LinkageCondition, LinkageAction } from '@hospital/shared';
import { evaluateExpression } from '@hospital/shared/src/utils/expression-engine';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** 数据源加载状态 */
export interface DataSourceState {
  data: any;
  loading: boolean;
  error: string | null;
  lastFetchTime: number;
}

/** 数据源加载状态映射 (key = dataSource.id) */
export type DataSourceMap = Record<string, DataSourceState>;

/** useDataManager 入参 */
export interface UseDataManagerOptions {
  /** 页面级 API 数据源列表 (来自 schema.dataSources) */
  dataSources?: PageDataSource[];
  /** 页面级 state schema, 定义初始值及类型 */
  stateSchema?: Record<string, any>;
  /** 页面 URL 参数 (从 Taro router 获取) */
  pageParams?: Record<string, any>;
}

/** useDataManager 返回值 */
export interface DataManager {
  /** 当前完整状态快照 */
  state: Record<string, any>;
  /** 各数据源的加载状态 */
  dataSources: DataSourceMap;
  /** 设置嵌套路径值 (dot-notation), 如 "form.name" */
  setData: (path: string, value: any) => void;
  /** 读取嵌套路径值 (dot-notation) */
  getData: (path: string) => any;
  /** 手动触发数据源请求, 可传入额外参数覆盖默认 params */
  fetchDataSource: (id: string, params?: Record<string, any>) => Promise<void>;
  /** 表达式求值, 自动注入 pageParams / apiData / formData / custom 变量 */
  evaluate: (expr: string) => any;
  /** 更新字段值并执行指定联动规则 */
  setDataAndExecuteLinkage: (
    fieldId: string,
    value: any,
    rules: LinkageRule[],
  ) => void;
}

// ---------------------------------------------------------------------------
// Helpers: dot-notation path resolution
// ---------------------------------------------------------------------------

/**
 * 根据 dot-notation 路径从对象中读取值.
 * e.g. getNestedValue({ a: { b: 1 } }, 'a.b') => 1
 */
function getNestedValue(obj: any, path: string): any {
  if (!path) return obj;
  if (obj == null) return undefined;
  const segments = path.split('.');
  let current: any = obj;
  for (const seg of segments) {
    if (current == null || typeof current !== 'object') return undefined;
    current = current[seg];
  }
  return current;
}

/**
 * 根据 dot-notation 路径设置值, 返回新对象 (immutable).
 * e.g. setNestedValue({ a: { b: 1 } }, 'a.b', 2) => { a: { b: 2 } }
 */
function setNestedValue(
  obj: Record<string, any>,
  path: string,
  value: any,
): Record<string, any> {
  const segments = path.split('.');
  if (segments.length === 0) return obj;

  const clone = { ...obj };
  let current: any = clone;

  for (let i = 0; i < segments.length - 1; i++) {
    const seg = segments[i];
    const child = current[seg];
    // 确保中间层是可展开的对象
    current[seg] =
      child != null && typeof child === 'object' && !Array.isArray(child)
        ? { ...child }
        : {};
    current = current[seg];
  }

  current[segments[segments.length - 1]] = value;
  return clone;
}

// ---------------------------------------------------------------------------
// 联动规则
// ---------------------------------------------------------------------------

/** 评估联动规则条件 */
export function evaluateLinkageCondition(
  condition: LinkageCondition,
  context: Record<string, any>,
): boolean {
  const sourceValue = context[condition.sourceFieldId];

  switch (condition.operator) {
    case 'equals':
      return sourceValue === condition.value;
    case 'notEquals':
      return sourceValue !== condition.value;
    case 'contains':
      return String(sourceValue).includes(String(condition.value));
    case 'greaterThan':
      return Number(sourceValue) > Number(condition.value);
    case 'lessThan':
      return Number(sourceValue) < Number(condition.value);
    case 'isEmpty':
      return sourceValue == null || sourceValue === '';
    case 'isNotEmpty':
      return sourceValue != null && sourceValue !== '';
    default:
      return false;
  }
}

/** 执行联动规则动作 */
export function executeLinkageAction(
  action: LinkageAction,
  _context: Record<string, any>,
  updateContext: (updates: Record<string, any>) => void,
): void {
  const updates: Record<string, any> = {};

  switch (action.type) {
    case 'setValue':
      updates[action.targetFieldId] = action.value;
      break;
    case 'setVisible':
      updates[`${action.targetFieldId}_visible`] = action.value === 'true' || action.value === true;
      break;
    case 'setDisabled':
      updates[`${action.targetFieldId}_disabled`] = action.value === 'true' || action.value === true;
      break;
    case 'setRequired':
      updates[`${action.targetFieldId}_required`] = action.value === 'true' || action.value === true;
      break;
  }

  updateContext(updates);
}

/** 执行节点的所有联动规则 */
export function executeLinkageRules(
  rules: LinkageRule[],
  context: Record<string, any>,
  updateContext: (updates: Record<string, any>) => void,
): void {
  for (const rule of rules) {
    if (!rule.enabled) continue;

    // 检查所有条件（AND 关系）
    const allConditionsMet = rule.conditions.every((cond) =>
      evaluateLinkageCondition(cond, context),
    );

    if (allConditionsMet) {
      // 执行所有动作
      for (const action of rule.actions) {
        executeLinkageAction(action, context, updateContext);
      }
    }
  }
}

// ---------------------------------------------------------------------------
// API 请求
// ---------------------------------------------------------------------------

/**
 * 调用后端 API (使用 Taro.request, 自动注入租户/鉴权 headers).
 */
async function requestApi(
  ds: ApiDataSource,
  pageParams: Record<string, any>,
  extraParams?: Record<string, any>,
): Promise<any> {
  // 合并 pageParams -> ds.params -> extraParams (后者覆盖前者)
  const mergedParams: Record<string, any> = {
    ...pageParams,
    ...ds.params,
    ...extraParams,
  };

  const header: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(ds.headers || {}),
  };

  // 注入租户信息
  const tenantCode = Taro.getStorageSync('tenantCode');
  if (tenantCode) {
    header['X-Tenant-Code'] = tenantCode;
  }

  const token = Taro.getStorageSync('token');
  if (token) {
    header['Authorization'] = `Bearer ${token}`;
  }

  const response = await Taro.request({
    url: ds.url,
    method: ds.method,
    header,
    data: mergedParams,
  });

  if (response.statusCode >= 200 && response.statusCode < 300) {
    const body = response.data;
    // 按 dataPath 提取
    if (ds.dataPath) {
      return getNestedValue(body, ds.dataPath);
    }
    return body;
  }

  throw new Error(`API ${ds.id} 请求失败: ${response.statusCode}`);
}

// ---------------------------------------------------------------------------
// useDataManager
// ---------------------------------------------------------------------------

/**
 * 低代码运行时页面级数据管理 Hook.
 *
 * @example
 * ```ts
 * const dm = useDataManager({
 *   dataSources: schema.dataSources,
 *   stateSchema: { form: { name: '', phone: '' } },
 *   pageParams: Taro.getCurrentInstance().router?.params,
 * });
 *
 * // 读写 state (支持嵌套路径)
 * dm.setData('form.name', '张三');
 * dm.getData('form.name'); // '张三'
 *
 * // 表达式求值 (自动注入作用域变量)
 * dm.evaluate('apiData.doctors.data.length > 0');
 * ```
 */
export function useDataManager(options: UseDataManagerOptions = {}): DataManager {
  const { dataSources = [], stateSchema = {}, pageParams = {} } = options;

  // ---- state ----
  const [state, setState] = useState<Record<string, any>>(() => ({
    ...stateSchema,
  }));

  // ---- data source states ----
  const [dsMap, setDsMap] = useState<DataSourceMap>(() => {
    const init: DataSourceMap = {};
    for (const ds of dataSources) {
      init[ds.id] = { data: null, loading: false, error: null, lastFetchTime: 0 };
    }
    return init;
  });

  // ---- refs 供 callbacks 读最新值 ----
  const stateRef = useRef(state);
  stateRef.current = state;

  const dsMapRef = useRef(dsMap);
  dsMapRef.current = dsMap;

  const dataSourcesRef = useRef(dataSources);
  dataSourcesRef.current = dataSources;

  const pageParamsRef = useRef(pageParams);
  pageParamsRef.current = pageParams;

  // ---- setData (immutable, dot-notation) ----
  const setData = useCallback((path: string, value: any) => {
    setState((prev) => setNestedValue(prev, path, value));
  }, []);

  // ---- setDataAndExecuteLinkage ----
  const setDataAndExecuteLinkage = useCallback(
    (fieldId: string, value: any, rules: LinkageRule[]) => {
      setState((prev) => {
        const afterField = setNestedValue(prev, fieldId, value);
        if (rules.length === 0) return afterField;

        const updates: Record<string, any> = {};
        executeLinkageRules(rules, afterField, (u) => {
          Object.assign(updates, u);
        });

        let merged = afterField;
        for (const [k, v] of Object.entries(updates)) {
          merged = setNestedValue(merged, k, v);
        }
        return merged;
      });
    },
    [],
  );

  // ---- getData ----
  const getData = useCallback((path: string) => {
    return getNestedValue(stateRef.current, path);
  }, []);

  // ---- fetchDataSource ----
  const fetchDataSource = useCallback(
    async (id: string, params?: Record<string, any>) => {
      const ds = dataSourcesRef.current.find((d) => d.id === id);
      if (!ds) {
        console.warn(`[DataManager] 数据源 "${id}" 不存在`);
        return;
      }

      // 标记 loading
      setDsMap((prev) => ({
        ...prev,
        [id]: { ...prev[id], loading: true, error: null },
      }));

      try {
        const result = await requestApi(ds, pageParamsRef.current, params);
        setDsMap((prev) => ({
          ...prev,
          [id]: {
            data: result,
            loading: false,
            error: null,
            lastFetchTime: Date.now(),
          },
        }));
      } catch (err: any) {
        const message = err?.message || '请求失败';
        console.error(`[DataManager] 数据源 "${id}" 请求出错:`, message);
        setDsMap((prev) => ({
          ...prev,
          [id]: { ...prev[id], loading: false, error: message },
        }));
      }
    },
    [],
  );

  // ---- evaluate (基于 expression-engine) ----
  const evaluate = useCallback((expr: string): any => {
    if (!expr) return undefined;

    const currentDs = dsMapRef.current;
    const currentState = stateRef.current;
    const currentParams = pageParamsRef.current;

    // 构建 apiData 作用域: { [dsId]: DataSourceState }
    const apiData: Record<string, DataSourceState> = {};
    for (const [id, dsState] of Object.entries(currentDs)) {
      apiData[id] = dsState;
    }

    // 变量作用域:
    //   pageParams - 路由参数
    //   apiData    - 各数据源结果/状态
    //   formData   - state 别名 (表单场景)
    //   state      - state 直接引用
    //   custom     - state 顶层 key 直接展开为顶层变量
    const ctx: Record<string, any> = {
      pageParams: currentParams,
      apiData,
      formData: currentState,
      state: currentState,
      ...currentState,
    };

    return evaluateExpression(expr, ctx);
  }, []);

  // ---- mount: 自动拉取 manual === false / undefined 的数据源 ----
  useEffect(() => {
    for (const ds of dataSources) {
      if (!ds.manual) {
        fetchDataSource(ds.id);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- 轮询 ----
  useEffect(() => {
    const timers: ReturnType<typeof setInterval>[] = [];

    for (const ds of dataSources) {
      if (ds.pollingInterval && ds.pollingInterval > 0) {
        const timer = setInterval(() => {
          fetchDataSource(ds.id);
        }, ds.pollingInterval);
        timers.push(timer);
      }
    }

    return () => {
      timers.forEach((t) => clearInterval(t));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    state,
    dataSources: dsMap,
    setData,
    getData,
    fetchDataSource,
    evaluate,
    setDataAndExecuteLinkage,
  };
}

export default useDataManager;
