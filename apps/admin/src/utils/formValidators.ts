/**
 * 表单验证器
 *
 * 提供可复用的表单验证规则和函数
 */

import { PATTERNS, MESSAGES, getCodePattern, getCodeMessage, type CodeFormatType } from '../constants/validation';

/**
 * 用户名验证规则
 */
export const usernameRules = {
  // 用户名格式验证
  pattern: {
    pattern: PATTERNS.USERNAME,
    message: MESSAGES.USERNAME,
  },

  // 用户名唯一性验证（需要传入检查函数）
  unique: (checkFn: (value: string) => Promise<{ exists: boolean }>) => async (_: unknown, value: string) => {
    if (!value) {
      return Promise.resolve();
    }

    try {
      const result = await checkFn(value);
      if (result.exists) {
        return Promise.reject('该用户名已存在');
      }
      return Promise.resolve();
    } catch (error) {
      // 验证接口失败时不阻止提交
      return Promise.resolve();
    }
  },
};

/**
 * 手机号验证规则
 */
export const phoneRules = {
  pattern: {
    pattern: PATTERNS.PHONE,
    message: MESSAGES.PHONE,
  },
};

/**
 * 座机号验证规则
 *
 * @example
 * ```tsx
 * <Form.Item
 *   name="landline"
 *   rules={[landlineRules.pattern]}
 * >
 *   <Input />
 * </Form.Item>
 * ```
 */
export const landlineRules = {
  pattern: {
    pattern: PATTERNS.LANDLINE,
    message: MESSAGES.LANDLINE,
  },
};

/**
 * 手机或座机验证规则
 *
 * @example
 * ```tsx
 * <Form.Item
 *   name="phone"
 *   rules={[phoneOrLandlineRules.pattern]}
 * >
 *   <Input />
 * </Form.Item>
 * ```
 */
export const phoneOrLandlineRules = {
  pattern: {
    pattern: PATTERNS.PHONE_OR_LANDLINE,
    message: MESSAGES.PHONE_OR_LANDLINE,
  },
};

/**
 * 身份证号验证规则
 */
export const idCardRules = {
  pattern: {
    pattern: PATTERNS.ID_CARD,
    message: MESSAGES.ID_CARD,
  },
};

/**
 * 邮箱验证规则
 */
export const emailRules = {
  type: 'email' as const,
  message: MESSAGES.EMAIL,
};

/**
 * 密码验证规则
 */
export const passwordRules = {
  min: {
    pattern: /^.{6,}$/,
    message: '密码至少6位',
  },

  medium: {
    pattern: /^(?=.*[a-zA-Z])(?=.*\d).{8,}$/,
    message: '密码至少8位，包含字母和数字',
  },

  strong: {
    pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{10,}$/,
    message: '密码至少10位，包含大小写字母、数字和特殊字符',
  },
};

/**
 * 确认密码验证器
 *
 * @param passwordFieldName 密码字段名称
 * @returns 验证规则
 *
 * @example
 * ```tsx
 * <Form.Item
 *   name="confirmPassword"
 *   dependencies={['password']}
 *   rules={confirmPasswordRules('password')}
 * >
 *   <Input.Password />
 * </Form.Item>
 * ```
 */
export const confirmPasswordRules = (passwordFieldName: string = 'password') => ({
  validator: (_: unknown, value: string, allValues: any) => {
    const password = allValues[passwordFieldName];

    // 如果两个密码都为空，不进行验证
    if (!password && !value) {
      return Promise.resolve();
    }

    // 如果有密码但没有确认密码
    if (password && !value) {
      return Promise.reject(new Error('请再次输入密码'));
    }

    // 如果两次密码不一致
    if (password !== value) {
      return Promise.reject(new Error('两次输入的密码不一致'));
    }

    return Promise.resolve();
  },
  dependencies: [passwordFieldName],
});

/**
 * URL 验证规则
 */
export const urlRules = {
  type: 'url' as const,
  message: MESSAGES.URL,
};

/**
 * 时间格式验证规则 (HH:mm)
 *
 * @example
 * ```tsx
 * <Form.Item
 *   name="startTime"
 *   rules={[timeRules.pattern]}
 * >
 *   <TimePicker format="HH:mm" />
 * </Form.Item>
 * ```
 */
export const timeRules = {
  pattern: {
    pattern: PATTERNS.TIME,
    message: MESSAGES.TIME,
  },
};

/**
 * 编码格式验证规则生成器
 *
 * 支持多种编码格式：小写、大写、slug、unicode
 *
 * @param format - 编码格式类型
 * @returns 验证规则
 *
 * @example
 * ```tsx
 * <Form.Item
 *   name="code"
 *   rules={[codeRules('lower').pattern]}
 * >
 *   <Input />
 * </Form.Item>
 * ```
 */
export const codeRules = (format: CodeFormatType = 'slug') => ({
  pattern: {
    pattern: getCodePattern(format),
    message: getCodeMessage(format),
  },
});

/**
 * 数字范围验证器
 *
 * @param min 最小值
 * @param max 最大值
 * @returns 验证规则
 *
 * @example
 * ```tsx
 * <Form.Item
 *   name="age"
 *   rules={numberRangeRules(0, 120)}
 * >
 *   <InputNumber />
 * </Form.Item>
 * ```
 */
export const numberRangeRules = (min: number, max: number) => ({
  type: 'number' as const,
  min,
  max,
  message: `请输入${min}到${max}之间的数字`,
});

/**
 * 字符串长度验证器
 *
 * @param min 最小长度
 * @param max 最大长度
 * @returns 验证规则
 *
 * @example
 * ```tsx
 * <Form.Item
 *   name="name"
 *   rules={stringLengthRules(2, 20)}
 * >
 *   <Input />
 * </Form.Item>
 * ```
 */
export const stringLengthRules = (min: number, max: number) => ({
  min,
  max,
  message: `请输入${min}到${max}个字符`,
});

/**
 * 必填验证器（带自定义消息）
 *
 * @param message 错误消息
 * @returns 验证规则
 *
 * @example
 * ```tsx
 * <Form.Item
 *   name="name"
 *   rules={requiredRules('请输入姓名')}
 * >
 *   <Input />
 * </Form.Item>
 * ```
 */
export const requiredRules = (message = '该字段为必填项') => ({
  required: true,
  message,
});

/**
 * 正则表达式验证器
 *
 * @param pattern 正则表达式
 * @param message 错误消息
 * @returns 验证规则
 *
 * @example
 * ```tsx
 * <Form.Item
 *   name="plateNumber"
 *   rules={[patternRules(
 *     /^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5,6}$/,
 *     '请输入正确的车牌号'
 *   )]}
 * >
 *   <Input />
 * </Form.Item>
 * ```
 */
export const patternRules = (pattern: RegExp, message: string) => ({
  pattern,
  message,
});

/**
 * 字段唯一性验证器
 *
 * 通用的字段唯一性验证，支持排除当前编辑项的ID
 *
 * @param checkFn - 检查函数，接收字段值和当前ID，返回检查结果
 * @param options - 配置选项
 * @returns 验证规则
 *
 * @example
 * ```tsx
 * // 基本用法
 * <Form.Item
 *   name="code"
 *   rules={[uniqueField(
 *     async (value) => {
 *       const result = await checkCodeExists(value);
 *       return !result.exists;
 *     },
 *     { message: '该编码已存在' }
 *   )]}
 * >
 *   <Input />
 * </Form.Item>
 *
 * // 编辑时排除当前项
 * <Form.Item
 *   name="code"
 *   rules={[uniqueField(
 *     async (value, currentId) => {
 *       const result = await checkCodeExists(value, currentId);
 *       return !result.exists;
 *     },
 *     {
 *     message: '该编码已存在',
 *     currentId: editingId,
 *     idField: 'id'
 *   }
 *   )]}
 * >
 *   <Input />
 * </Form.Item>
 * ```
 */
export const uniqueField = (
  checkFn: (value: any, currentId?: string | number) => Promise<boolean>,
  options?: {
    message?: string;
    currentId?: string | number;
    idField?: string;
  }
) => ({
  validator: async (_: unknown, value: any) => {
    if (!value) {
      return Promise.resolve();
    }

    const { message = '该值已存在', currentId } = options || {};

    try {
      const valid = await checkFn(value, currentId);
      if (!valid) {
        return Promise.reject(new Error(message));
      }
      return Promise.resolve();
    } catch (error) {
      // 验证接口失败时不阻止提交
      return Promise.resolve();
    }
  },
});

/**
 * 组合多个验证规则
 *
 * 辅助函数，用于组合多个验证规则到一个数组中
 *
 * @param rules - 验证规则数组
 * @returns 验证规则数组
 *
 * @example
 * ```tsx
 * <Form.Item
 *   name="username"
 *   rules={combinedRules(
 *     requiredRules('请输入用户名'),
 *     usernameRules.pattern,
 *     uniqueField(checkUsername, { message: '用户名已存在' })
 *   )}
 * >
 *   <Input />
 * </Form.Item>
 * ```
 */
export const combinedRules = (...rules: Array<Record<string, any>>) => {
  return rules;
};

/**
 * 条件验证规则
 *
 * 根据条件决定是否应用某个验证规则
 *
 * @param condition - 条件函数，接收表单所有值，返回是否应用规则
 * @param rule - 要应用的条件规则
 * @returns 验证规则
 *
 * @example
 * ```tsx
 * <Form.Item
 *   name="phone"
 *   rules={conditionalRule(
 *     (allValues) => allValues.contactMethod === 'phone',
 *     phoneRules.pattern
 *   )}
 * >
 *   <Input />
 * </Form.Item>
 * ```
 */
export const conditionalRule = (
  condition: (allValues: any) => boolean,
  rule: Record<string, any>
) => ({
  validator: (_: unknown, value: any, allValues: any) => {
    if (!condition(allValues)) {
      return Promise.resolve();
    }

    // 如果规则有 pattern，进行正则验证
    if (rule.pattern && value) {
      if (!rule.pattern.test(value)) {
        return Promise.reject(new Error(rule.message));
      }
    }

    // 如果规则有 validator，调用它
    if (rule.validator) {
      return rule.validator(_, value, allValues);
    }

    return Promise.resolve();
  },
});

/**
 * 自定义异步验证器
 *
 * @param validator 验证函数
 * @param message 错误消息
 * @returns 验证规则
 *
 * @example
 * ```tsx
 * <Form.Item
 *   name="code"
 *   rules={asyncValidator(
 *     async (value) => {
 *       const result = await checkCodeExists(value);
 *       return !result.exists;
 *     },
 *     '该编码已存在'
 *   )}
 * >
 *   <Input />
 * </Form.Item>
 * ```
 */
export const asyncValidator = (
  validator: (value: any) => Promise<boolean>,
  message: string
) => ({
  validator: async (_: unknown, value: any) => {
    if (!value) {
      return Promise.resolve();
    }

    try {
      const valid = await validator(value);
      if (!valid) {
        return Promise.reject(new Error(message));
      }
      return Promise.resolve();
    } catch (error) {
      // 验证接口失败时不阻止提交
      return Promise.resolve();
    }
  },
});

/**
 * 经度验证规则（中国境内：73.5°E ~ 135.5°E）
 *
 * @example
 * ```tsx
 * <Form.Item name="longitude" rules={[longitudeRules]}>
 *   <Input />
 * </Form.Item>
 * ```
 */
export const longitudeRules = {
  validator: (_: unknown, value: string | number) => {
    if (!value) return Promise.resolve();
    const num = Number(value);
    if (isNaN(num)) return Promise.reject(new Error('请输入有效的经度'));
    if (num < 73.5 || num > 135.5) return Promise.reject(new Error('经度超出中国境内范围（73.5 ~ 135.5）'));
    return Promise.resolve();
  },
};

/**
 * 纬度验证规则（中国境内：3.8°N ~ 53.5°N）
 *
 * @example
 * ```tsx
 * <Form.Item name="latitude" rules={[latitudeRules]}>
 *   <Input />
 * </Form.Item>
 * ```
 */
export const latitudeRules = {
  validator: (_: unknown, value: string | number) => {
    if (!value) return Promise.resolve();
    const num = Number(value);
    if (isNaN(num)) return Promise.reject(new Error('请输入有效的纬度'));
    if (num < 3.8 || num > 53.5) return Promise.reject(new Error('纬度超出中国境内范围（3.8 ~ 53.5）'));
    return Promise.resolve();
  },
};

/**
 * 常用验证器集合
 */
export const validators = {
  /** 必填 */
  required: requiredRules,
  /** 用户名 */
  username: usernameRules,
  /** 手机号 */
  phone: phoneRules,
  /** 座机号 */
  landline: landlineRules,
  /** 手机或座机 */
  phoneOrLandline: phoneOrLandlineRules,
  /** 身份证 */
  idCard: idCardRules,
  /** 邮箱 */
  email: emailRules,
  /** 密码 */
  password: passwordRules,
  /** 确认密码 */
  confirmPassword: confirmPasswordRules,
  /** URL */
  url: urlRules,
  /** 时间格式 */
  time: timeRules,
  /** 编码格式 */
  code: codeRules,
  /** 数字范围 */
  numberRange: numberRangeRules,
  /** 字符串长度 */
  stringLength: stringLengthRules,
  /** 正则表达式 */
  pattern: patternRules,
  /** 异步验证 */
  async: asyncValidator,
  /** 字段唯一性 */
  uniqueField: uniqueField,
  /** 组合规则 */
  combined: combinedRules,
  /** 条件规则 */
  conditional: conditionalRule,
  /** 经度（中国境内） */
  longitude: longitudeRules,
  /** 纬度（中国境内） */
  latitude: latitudeRules,
};
