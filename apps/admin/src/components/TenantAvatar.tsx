/** 租户头像组件 */

import React, { useMemo } from 'react';
import { Avatar } from 'antd';
import { BankOutlined } from '@ant-design/icons';

/** 品牌配置结构 */
interface BrandingConfig {
  logoUrl?: string;
  themeColor?: string;
  [key: string]: unknown;
}

/** 租户数据（取所需字段，避免强耦合） */
export interface TenantLike {
  name?: string;
  brandingConfig?: string;
}

export interface TenantAvatarProps {
  /** 租户对象 */
  tenant?: TenantLike | null;
  /** 头像尺寸 */
  size?: number | 'small' | 'default' | 'large';
  /** 自定义样式 */
  style?: React.CSSProperties;
  /** 自定义类名 */
  className?: string;
}

/** 预设背景色（按租户名 hash 轮转） */
const AVATAR_COLORS = [
  '#1677ff',
  '#52c41a',
  '#fa8c16',
  '#722ed1',
  '#13c2c2',
  '#eb2f96',
  '#2f54eb',
  '#faad14',
];

/** 根据名称生成稳定的颜色索引 */
const getColorByName = (name: string): string => {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
};

/** 解析 brandingConfig JSON 字符串 */
const parseBranding = (config?: string): BrandingConfig | null => {
  if (!config) return null;
  try {
    return JSON.parse(config);
  } catch {
    return null;
  }
};

/** 获取租户名称首字符 */
const getInitial = (name?: string): string => {
  if (!name) return '';
  return name.charAt(0).toUpperCase();
};

/** 租户头像 */
const TenantAvatar: React.FC<TenantAvatarProps> = ({
  tenant,
  size = 32,
  style,
  className,
}) => {
  const branding = useMemo(() => parseBranding(tenant?.brandingConfig), [tenant?.brandingConfig]);
  const logo = branding?.logoUrl;
  const name = tenant?.name || '';
  const initial = getInitial(name);
  const bgColor = getColorByName(name);

  if (logo) {
    return (
      <Avatar
        src={logo}
        size={size}
        className={className}
        style={style}
      />
    );
  }

  if (initial) {
    return (
      <Avatar
        size={size}
        className={className}
        style={{
          backgroundColor: bgColor,
          color: '#fff',
          fontWeight: 500,
          ...style,
        }}
      >
        {initial}
      </Avatar>
    );
  }

  return (
    <Avatar
      icon={<BankOutlined />}
      size={size}
      className={className}
      style={{
        backgroundColor: '#f0f0f0',
        color: '#999',
        ...style,
      }}
    />
  );
};

export default TenantAvatar;
