/**
 * 表单验证器
 *
 * 提供可复用的表单验证规则和函数
 */

/**
 * 用户名验证规则
 */
export const usernameRules = {
  // 用户名格式验证
  pattern: {
    pattern: /^[a-z0-9_]{4,20}$/,
    message: '用户名只能包含小写字母、数字、下划线，长度4-20位',
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
    pattern: /^1[3-9]\d{9}$/,
    message: '请输入正确的手机号',
  },
};

/**
 * 身份证号验证规则
 */
export const idCardRules = {
  pattern: {
    pattern: /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/,
    message: '请输入正确的身份证号',
  },
};

/**
 * 邮箱验证规则
 */
export const emailRules = {
  type: 'email' as const,
  message: '请输入正确的邮箱地址',
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
  message: '请输入正确的URL地址',
};

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
 *   rules={patternRules(
 *     /^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5,6}$/,
 *     '请输入正确的车牌号'
 *   )}
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
 * 常用验证器集合
 */
export const validators = {
  /** 必填 */
  required: requiredRules,
  /** 用户名 */
  username: usernameRules,
  /** 手机号 */
  phone: phoneRules,
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
  /** 数字范围 */
  numberRange: numberRangeRules,
  /** 字符串长度 */
  stringLength: stringLengthRules,
  /** 正则表达式 */
  pattern: patternRules,
  /** 异步验证 */
  async: asyncValidator,
};
