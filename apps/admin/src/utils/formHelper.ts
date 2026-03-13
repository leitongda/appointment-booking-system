/**
 * 表单工具函数
 *
 * 提供表单数据处理、转换和辅助函数，简化表单操作
 */

/**
 * 开关值转换方向
 */
export type SwitchDirection = 'toNumber' | 'toBoolean';

/**
 * 表单准备选项
 */
export interface FormPrepareOptions<T> {
  /** 需要进行开关值转换的字段 */
  switchFields?: (keyof T)[];
  /** 需要进行日期格式化的字段 */
  dateFields?: (keyof T)[];
  /** 默认值 */
  defaultValues?: Partial<T>;
}

/**
 * ============================================================================
 * 开关值转换函数
 * ============================================================================
 */

/**
 * 将布尔值转换为数字（用于表单提交）
 *
 * @param value 布尔值
 * @returns 0 或 1
 *
 * @example
 * switchToNumber(true)  // => 1
 * switchToNumber(false) // => 0
 */
export function switchToNumber(value: boolean | undefined): number {
  return value === true ? 1 : 0;
}

/**
 * 将数字转换为布尔值（用于表单初始化）
 *
 * @param value 数字（0 或 1）
 * @returns true 或 false
 *
 * @example
 * numberToSwitch(1) // => true
 * numberToSwitch(0) // => false
 * numberToSwitch(2) // => false
 */
export function numberToSwitch(value: number | undefined): boolean {
  return value === 1;
}

/**
 * 批量转换对象中的开关字段
 *
 * @param values 原始对象
 * @param fields 需要转换的字段名数组
 * @param direction 转换方向：'toNumber'（布尔转数字）或 'toBoolean'（数字转布尔）
 * @returns 转换后的对象副本
 *
 * @example
 * // 布尔转数字（用于提交）
 * convertSwitches(
 *   { name: 'test', active: true, published: false },
 *   ['active', 'published'],
 *   'toNumber'
 * )
 * // => { name: 'test', active: 1, published: 0 }
 *
 * @example
 * // 数字转布尔（用于初始化）
 * convertSwitches(
 *   { name: 'test', active: 1, published: 0 },
 *   ['active', 'published'],
 *   'toBoolean'
 * )
 * // => { name: 'test', active: true, published: false }
 */
export function convertSwitches<T extends Record<string, any>>(
  values: T,
  fields: (keyof T)[],
  direction: SwitchDirection
): Partial<T> {
  const result = { ...values };
  const converter = direction === 'toNumber' ? switchToNumber : numberToSwitch;

  for (const field of fields) {
    if (field in result) {
      result[field] = converter(result[field] as any) as T[keyof T];
    }
  }

  return result;
}

/**
 * ============================================================================
 * 表单数据处理函数
 * ============================================================================
 */

/**
 * 判断值是否为空（undefined、null、空字符串、空数组）
 *
 * @param value 待检查的值
 * @returns 是否为空
 */
function isEmpty(value: any): boolean {
  if (value === undefined || value === null) return true;
  if (typeof value === 'string' && value.trim() === '') return true;
  if (Array.isArray(value) && value.length === 0) return true;
  return false;
}

/**
 * 清理对象中的空值
 *
 * 移除 undefined、null、空字符串等空值，用于提交前的数据清理
 *
 * @param values 原始对象
 * @returns 清理后的对象副本
 *
 * @example
 * cleanEmptyValues({
 *   name: 'test',
 *   description: '',
 *   count: 0,
 *   active: undefined,
 *   tags: []
 * })
 * // => { name: 'test', count: 0 }
 *
 * @note 保留 0 和 false，它们被视为有效值
 */
export function cleanEmptyValues<T extends Record<string, any>>(values: T): Partial<T> {
  const result: Partial<T> = {};

  for (const key in values) {
    if (Object.prototype.hasOwnProperty.call(values, key)) {
      const value = values[key];
      // 保留 0 和 false，只移除 undefined、null、空字符串、空数组
      if (!isEmpty(value) || value === 0 || value === false) {
        result[key] = value;
      }
    }
  }

  return result;
}

/**
 * 提取变化的字段
 *
 * 对比原始数据和当前数据，返回发生变化的字段
 *
 * @param original 原始数据
 * @param current 当前数据
 * @returns 包含变化字段的对象
 *
 * @example
 * getChangedFields(
 *   { name: 'old', count: 1, active: true },
 *   { name: 'new', count: 1, active: true }
 * )
 * // => { name: 'new' }
 */
export function getChangedFields<T extends Record<string, any>>(
  original: T,
  current: Partial<T>
): Partial<T> {
  const changed: Partial<T> = {};

  for (const key in current) {
    if (Object.prototype.hasOwnProperty.call(current, key)) {
      const currentValue = current[key];
      const originalValue = original[key];

      // 处理 undefined 的情况
      if (currentValue !== undefined && currentValue !== originalValue) {
        changed[key] = currentValue;
      }
    }
  }

  return changed;
}

/**
 * 深度合并表单值
 *
 * 处理嵌套对象的合并，常用于处理分组的表单字段
 *
 * @param base 基础对象
 * @param updates 更新的对象
 * @returns 合并后的对象
 *
 * @example
 * mergeFormValues(
 *   { user: { name: 'old', age: 20 }, status: 1 },
 *   { user: { name: 'new' }, status: 2 }
 * )
 * // => { user: { name: 'new', age: 20 }, status: 2 }
 */
export function mergeFormValues<T extends Record<string, any>>(
  base: Partial<T>,
  updates: Partial<T>
): Partial<T> {
  const result = { ...base };

  for (const key in updates) {
    if (Object.prototype.hasOwnProperty.call(updates, key)) {
      const value = updates[key];
      const baseValue = result[key];

      // 如果两者都是对象，递归合并
      if (
        typeof value === 'object' &&
        value !== null &&
        !Array.isArray(value) &&
        typeof baseValue === 'object' &&
        baseValue !== null &&
        !Array.isArray(baseValue)
      ) {
        result[key] = mergeFormValues(baseValue as any, value as any) as T[keyof T];
      } else {
        result[key] = value;
      }
    }
  }

  return result;
}

/**
 * ============================================================================
 * 表单字段辅助函数
 * ============================================================================
 */

/**
 * 生成嵌套字段名
 *
 * 用于 ProForm.Group 或 Form.List 等嵌套场景
 *
 * @param prefix 前缀（父字段名或索引）
 * @param field 当前字段名
 * @returns 嵌套字段名
 *
 * @example
 * getNestedFieldName('user', 'name')        // => 'user.name'
 * getNestedFieldName('users[0]', 'name')    // => 'users[0].name'
 * getNestedFieldName('', 'name')            // => 'name'
 */
export function getNestedFieldName(prefix: string, field: string): string {
  if (!prefix) return field;
  return `${prefix}.${field}`;
}

/**
 * 解析嵌套字段路径
 *
 * 将点分隔的路径字符串转换为路径数组
 *
 * @param path 字段路径（如 'user.profile.name'）
 * @returns 路径数组
 *
 * @example
 * parseFieldPath('user.profile.name') // => ['user', 'profile', 'name']
 * parseFieldPath('user[0].name')      // => ['user', '0', 'name']
 */
export function parseFieldPath(path: string): string[] {
  return path.replace(/\[/g, '.').replace(/\]/g, '').split('.').filter(Boolean);
}

/**
 * 获取嵌套字段值
 *
 * 根据点分隔的路径从对象中获取值
 *
 * @param obj 目标对象
 * @param path 字段路径（支持点分隔和数组索引）
 * @returns 字段值，如果路径不存在则返回 undefined
 *
 * @example
 * getNestedFieldValue({ user: { profile: { name: 'test' } } }, 'user.profile.name')
 * // => 'test'
 *
 * getNestedFieldValue({ items: [{ id: 1 }] }, 'items[0].id')
 * // => 1
 */
export function getNestedFieldValue<T = any>(obj: any, path: string): T | undefined {
  const keys = parseFieldPath(path);
  let current = obj;

  for (const key of keys) {
    if (current === null || current === undefined) {
      return undefined;
    }
    current = current[key];
  }

  return current as T;
}

/**
 * 设置嵌套字段值
 *
 * 根据点分隔的路径在对象中设置值，自动创建中间对象
 *
 * @param obj 目标对象
 * @param path 字段路径（支持点分隔和数组索引）
 * @param value 要设置的值
 *
 * @example
 * const obj = {};
 * setNestedFieldValue(obj, 'user.profile.name', 'test');
 * // obj => { user: { profile: { name: 'test' } } }
 *
 * @example
 * const obj = { items: [] };
 * setNestedFieldValue(obj, 'items[0].id', 1);
 * // obj => { items: [{ id: 1 }] }
 */
export function setNestedFieldValue(obj: any, path: string, value: any): void {
  const keys = parseFieldPath(path);
  let current = obj;

  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];
    const nextKey = keys[i + 1];

    // 数组索引处理
    const isArrayIndex = /^\d+$/.test(nextKey);

    if (!(key in current) || current[key] === null || current[key] === undefined) {
      current[key] = isArrayIndex ? [] : {};
    }

    current = current[key];
  }

  const lastKey = keys[keys.length - 1];
  current[lastKey] = value;
}

/**
 * ============================================================================
 * 表单初始化辅助函数
 * ============================================================================
 */

/**
 * 为编辑表单准备初始值
 *
 * 处理开关值转换（数字 -> 布尔）、日期格式化等
 *
 * @param data 后端返回的原始数据
 * @param options 配置选项
 * @returns 适合表单使用的初始值
 *
 * @example
 * prepareInitialValues(
 *   { id: 1, name: 'test', status: 1, active: 0 },
 *   {
 *     switchFields: ['status', 'active'],
 *     defaultValues: { createdAt: new Date() }
 *   }
 * )
 * // => { id: 1, name: 'test', status: true, active: false, createdAt: new Date() }
 */
export function prepareInitialValues<T extends Record<string, any>>(
  data: T,
  options?: FormPrepareOptions<T>
): Partial<T> {
  const result: Partial<T> = { ...data };
  const opts = options || {};

  // 开关值转换：数字 -> 布尔
  if (opts.switchFields && opts.switchFields.length > 0) {
    const converted = convertSwitches(data, opts.switchFields, 'toBoolean');
    Object.assign(result, converted);
  }

  // 默认值合并
  if (opts.defaultValues) {
    Object.assign(result, opts.defaultValues);
  }

  return result;
}

/**
 * 为提交准备数据
 *
 * 与 prepareInitialValues 相反，将表单值转换为后端需要的格式
 *
 * @param values 表单值
 * @param options 配置选项
 * @returns 适合提交给后端的数据
 *
 * @example
 * prepareSubmitValues(
 *   { name: 'test', status: true, active: false, description: '' },
 *   { switchFields: ['status', 'active'] }
 * )
 * // => { name: 'test', status: 1, active: 0 }
 * （description 被移除因为是空字符串）
 */
export function prepareSubmitValues<T extends Record<string, any>>(
  values: T,
  options?: FormPrepareOptions<T>
): Partial<T> {
  let result = cleanEmptyValues(values);
  const opts = options || {};

  // 开关值转换：布尔 -> 数字
  if (opts.switchFields && opts.switchFields.length > 0) {
    const converted = convertSwitches(values, opts.switchFields, 'toNumber');
    result = { ...result, ...converted };
  }

  return result;
}

/**
 * ============================================================================
 * 其他辅助函数
 * ============================================================================
 */

/**
 * 检查表单值是否有变化
 *
 * @param original 原始数据
 * @param current 当前表单值
 * @returns 是否有变化
 *
 * @example
 * hasFormChanges(
 *   { name: 'test', status: 1 },
 *   { name: 'test', status: 1 }
 * )
 * // => false
 *
 * hasFormChanges(
 *   { name: 'test', status: 1 },
 *   { name: 'new', status: 1 }
 * )
 * // => true
 */
export function hasFormChanges<T extends Record<string, any>>(
  original: T,
  current: Partial<T>
): boolean {
  return Object.keys(getChangedFields(original, current)).length > 0;
}

/**
 * 重置对象为默认值
 *
 * 将指定字段设置为其默认值
 *
 * @param values 原始对象
 * @param defaults 默认值映射
 * @returns 重置后的对象
 *
 * @example
 * resetFieldsToDefaults(
 *   { name: 'test', count: 5, active: true },
 *   { count: 0, active: false }
 * )
 * // => { name: 'test', count: 0, active: false }
 */
export function resetFieldsToDefaults<T extends Record<string, any>>(
  values: T,
  defaults: Partial<T>
): Partial<T> {
  return { ...values, ...defaults };
}

/**
 * 从对象中选取指定字段
 *
 * @param obj 源对象
 * @param fields 要选取的字段名数组
 * @returns 包含指定字段的新对象
 *
 * @example
 * pickFields(
 *   { name: 'test', count: 1, active: true, extra: 'data' },
 *   ['name', 'count']
 * )
 * // => { name: 'test', count: 1 }
 */
export function pickFields<T extends Record<string, any>, K extends keyof T>(
  obj: T,
  fields: K[]
): Pick<T, K> {
  const result = {} as Pick<T, K>;

  for (const field of fields) {
    if (field in obj) {
      result[field] = obj[field];
    }
  }

  return result;
}

/**
 * 从对象中排除指定字段
 *
 * @param obj 源对象
 * @param fields 要排除的字段名数组
 * @returns 不包含指定字段的新对象
 *
 * @example
 * omitFields(
 *   { name: 'test', count: 1, password: 'secret' },
 *   ['password']
 * )
 * // => { name: 'test', count: 1 }
 */
export function omitFields<T extends Record<string, any>, K extends keyof T>(
  obj: T,
  fields: K[]
): Omit<T, K> {
  const result = { ...obj } as any;

  for (const field of fields) {
    delete result[field];
  }

  return result;
}
