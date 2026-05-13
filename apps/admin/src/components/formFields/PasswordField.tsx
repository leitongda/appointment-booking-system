/**
 * 密码字段组件
 *
 * 功能：
 * - 包含密码输入和确认密码两个输入框
 * - 内置密码强度验证（可选配置强度级别）
 * - 内置密码一致性验证
 * - 支持显示/隐藏密码
 * - 新增/编辑模式自适应（编辑模式下可不填写密码）
 */
import { ProFormText } from '@ant-design/pro-components';
import { Space, Progress } from 'antd';
import { EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons';
import React, { useState, useEffect } from 'react';

/**
 * 密码强度级别
 */
export type PasswordStrengthLevel = 'min' | 'medium' | 'strong';

/**
 * 密码强度配置
 */
interface PasswordStrengthConfig {
  /** 最小长度 */
  minLength: number;
  /** 是否需要大写字母 */
  requireUppercase: boolean;
  /** 是否需要小写字母 */
  requireLowercase: boolean;
  /** 是否需要数字 */
  requireNumber: boolean;
  /** 是否需要特殊字符 */
  requireSpecialChar: boolean;
}

/**
 * 密码强度配置映射
 */
const PASSWORD_STRENGTH_CONFIG: Record<PasswordStrengthLevel, PasswordStrengthConfig> = {
  min: {
    minLength: 6,
    requireUppercase: false,
    requireLowercase: false,
    requireNumber: false,
    requireSpecialChar: false,
  },
  medium: {
    minLength: 8,
    requireUppercase: false,
    requireLowercase: true,
    requireNumber: true,
    requireSpecialChar: false,
  },
  strong: {
    minLength: 10,
    requireUppercase: true,
    requireLowercase: true,
    requireNumber: true,
    requireSpecialChar: true,
  },
};

/**
 * 密码字段组件属性
 */
export interface PasswordFieldProps {
  /** 表单项名称前缀（password 和 confirmPassword） */
  namePrefix?: string;
  /** 密码字段标签 */
  label?: string;
  /** 确认密码字段标签 */
  confirmLabel?: string;
  /** 是否必填 */
  required?: boolean;
  /** 密码强度级别 */
  strengthLevel?: PasswordStrengthLevel;
  /** 是否显示密码强度指示器 */
  showStrengthIndicator?: boolean;
  /** 是否为编辑模式（编辑模式下可以不填密码） */
  isEdit?: boolean;
  /** 占位符文本 */
  placeholder?: string;
  /** 确认密码占位符文本 */
  confirmPlaceholder?: string;
  /** 密码框宽度 */
  width?: number | 'xl' | 'lg' | 'md' | 'sm' | 'xs';
  /** 额外的提示信息 */
  extra?: string;
}

/**
 * 计算密码强度
 * @param password 密码
 * @param level 强度级别配置
 * @returns 强度分数 0-100
 */
function calculatePasswordStrength(password: string, level: PasswordStrengthConfig): number {
  let score = 0;

  // 长度检查
  if (password.length >= level.minLength) {
    score += 25;
  }

  // 大写字母检查
  if (level.requireUppercase && /[A-Z]/.test(password)) {
    score += 25;
  } else if (!level.requireUppercase && /[A-Z]/.test(password)) {
    score += 10;
  }

  // 小写字母检查
  if (level.requireLowercase && /[a-z]/.test(password)) {
    score += 25;
  } else if (!level.requireLowercase && /[a-z]/.test(password)) {
    score += 10;
  }

  // 数字检查
  if (level.requireNumber && /\d/.test(password)) {
    score += 25;
  } else if (!level.requireNumber && /\d/.test(password)) {
    score += 10;
  }

  // 特殊字符检查
  if (level.requireSpecialChar && /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
    score += 25;
  } else if (!level.requireSpecialChar && /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
    score += 15;
  }

  return Math.min(score, 100);
}

/**
 * 获取强度等级颜色
 */
function getStrengthColor(score: number): string {
  if (score < 40) return '#ff4d4f';
  if (score < 70) return '#faad14';
  return '#52c41a';
}

/**
 * 获取强度等级文本
 */
function getStrengthText(score: number): string {
  if (score < 40) return '弱';
  if (score < 70) return '中';
  return '强';
}

/**
 * 生成密码验证规则
 */
function generatePasswordRules(
  config: PasswordStrengthConfig,
  isEdit: boolean,
  required: boolean,
): any[] {
  const rules: any[] = [];

  if (!isEdit || required) {
    rules.push({ required: true, message: '请输入密码' });
  }

  rules.push({
    min: config.minLength,
    message: `密码至少需要 ${config.minLength} 个字符`,
  });

  if (config.requireUppercase) {
    rules.push({
      pattern: /[A-Z]/,
      message: '密码必须包含大写字母',
    });
  }

  if (config.requireLowercase) {
    rules.push({
      pattern: /[a-z]/,
      message: '密码必须包含小写字母',
    });
  }

  if (config.requireNumber) {
    rules.push({
      pattern: /\d/,
      message: '密码必须包含数字',
    });
  }

  if (config.requireSpecialChar) {
    rules.push({
      pattern: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/,
      message: '密码必须包含特殊字符',
    });
  }

  return rules;
}

/**
 * 密码字段组件
 *
 * @example
 * ```tsx
 * // 基础用法（新增模式）
 * <PasswordField />
 *
 * // 编辑模式
 * <PasswordField isEdit={true} />
 *
 * // 强密码模式
 * <PasswordField strengthLevel="strong" showStrengthIndicator={true} />
 *
 * // 自定义名称前缀
 * <PasswordField namePrefix="doctor" label="医生密码" />
 * ```
 */
const PasswordField: React.FC<PasswordFieldProps> = ({
  namePrefix = '',
  label = '密码',
  confirmLabel = '确认密码',
  required = true,
  strengthLevel = 'min',
  showStrengthIndicator = false,
  isEdit = false,
  placeholder = '请输入密码',
  confirmPlaceholder = '请再次输入密码',
  width = 'md',
  extra,
}) => {
  const passwordName = namePrefix ? `${namePrefix}Password` : 'password';
  const confirmPasswordName = namePrefix ? `${namePrefix}ConfirmPassword` : 'confirmPassword';
  const [password, setPassword] = useState('');
  const [strength, setStrength] = useState(0);
  const config = PASSWORD_STRENGTH_CONFIG[strengthLevel];

  // 监听密码变化，更新强度指示器
  useEffect(() => {
    if (showStrengthIndicator) {
      const newStrength = calculatePasswordStrength(password, config);
      setStrength(newStrength);
    }
  }, [password, showStrengthIndicator, config]);

  // 构建提示信息
  const buildExtra = () => {
    const tips: string[] = [];
    tips.push(`密码至少需要 ${config.minLength} 个字符`);
    if (config.requireUppercase) tips.push('大写字母');
    if (config.requireLowercase) tips.push('小写字母');
    if (config.requireNumber) tips.push('数字');
    if (config.requireSpecialChar) tips.push('特殊字符');
    return tips.join('、');
  };

  const defaultExtra = strengthLevel !== 'min' ? buildExtra() : undefined;

  return (
    <Space style={{ width: '100%' }}>
      {/* 密码输入框 */}
      <ProFormText.Password
        name={passwordName}
        label={label}
        width={width}
        placeholder={isEdit ? '不修改请留空' : placeholder}
        fieldProps={{
          autoComplete: 'new-password',
          iconRender: (visible) => (visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />),
          onChange: (e) => setPassword(e.target.value),
        }}
        rules={generatePasswordRules(config, isEdit, required)}
        extra={extra || defaultExtra}
      />

      {/* 密码强度指示器 */}
      {showStrengthIndicator && password && (
        <div style={{ width: width === 'md' ? 328 : width === 'lg' ? 480 : width, marginTop: -8 }}>
          <Progress
            percent={strength}
            strokeColor={getStrengthColor(strength)}
            showInfo={false}
            size="small"
          />
          <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
            密码强度：<span style={{ color: getStrengthColor(strength) }}>{getStrengthText(strength)}</span>
          </div>
        </div>
      )}

      {/* 确认密码输入框（仅在非编辑模式或明确要求时显示） */}
      {!isEdit && (
        <ProFormText.Password
          name={confirmPasswordName}
          label={confirmLabel}
          width={width}
          placeholder={confirmPlaceholder}
          fieldProps={{
            autoComplete: 'new-password',
            iconRender: (visible) => (visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />),
          }}
          dependencies={[passwordName]}
          rules={[
            ({ getFieldValue }) => ({
              validator(_, value) {
                const pwd = getFieldValue(passwordName);
                if (!pwd && !value) {
                  return Promise.resolve();
                }
                if (pwd && !value) {
                  return Promise.reject(new Error('请再次输入密码'));
                }
                if (pwd !== value) {
                  return Promise.reject(new Error('两次输入的密码不一致'));
                }
                return Promise.resolve();
              },
            }),
          ]}
        />
      )}
    </Space>
  );
};

export default PasswordField;
