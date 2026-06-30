/**
 * Settings tab 共享类型定义。
 *
 * 每个 tab 组件接收自己需要的 props，由父组件 SettingsPage 统一装配。
 * 这样每个 tab 是独立可测试的纯展示组件，不含业务逻辑（逻辑留在父组件）。
 */
import type {
  BookingSettings,
  HospitalInfo,
  BookingFieldConfig,
  PatientCardConfig,
  BlacklistItem,
  EmailConfig,
  ImageConfig,
  SmsConfig,
  SecurityConfig,
  SourceReleaseConfig,
} from '@hospital/api';
import type { StoreWechatConfig } from '@hospital/shared';

// ===================== 通用 =====================

/** 所有 tab 共用的基础权限 */
export interface BaseTabProps {
  canEdit: boolean;
  loading?: boolean;
}

// ===================== BookingTab =====================

export interface BookingTabProps extends BaseTabProps {
  bookingSettings: BookingSettings | null;
  selectedBookingStoreId: string;
  stores: { id: string; name: string }[];
  onStoreChange: (storeId: string) => void;
  onSubmit: (values: any) => Promise<void>;
}

// ===================== HospitalTab =====================

export interface HospitalTabProps extends BaseTabProps {
  hospitalInfo: HospitalInfo | null;
  onSubmit: (values: any) => Promise<void>;
}

// ===================== BookingFieldsTab =====================

export interface BookingFieldsTabProps extends BaseTabProps {
  bookingFields: BookingFieldConfig[];
  onFieldChange: (field: string, key: 'enabled' | 'required', value: boolean) => Promise<void>;
}

// ===================== PatientCardTab =====================

export interface PatientCardTabProps extends BaseTabProps {
  patientCardConfig: PatientCardConfig | null;
  onSubmit: (values: any) => Promise<void>;
}

// ===================== BlacklistTab =====================

export interface BlacklistTabProps {
  blacklist: BlacklistItem[];
  blacklistTotal: number;
  blacklistPage: number;
  blacklistKeyword: string;
  blacklistLoading: boolean;
  onLoadBlacklist: (page?: number, keyword?: string) => void;
  onAddBlacklist: (values: any) => Promise<boolean>;
  onRemoveBlacklist: (id: string) => Promise<void>;
  canAdd: boolean;
  canDelete: boolean;
  stores: { id: string; name: string }[];
  addModalVisible: boolean;
  onAddModalChange: (visible: boolean) => void;
}

// ===================== EmailTab =====================

export interface EmailTabProps extends BaseTabProps {
  emailConfig: EmailConfig | null;
  onSubmit: (values: any) => Promise<void>;
}

// ===================== WechatTab =====================

export interface WechatTabProps extends BaseTabProps {
  selectedStoreId: string;
  stores: { id: string; name: string }[];
  storeWechatConfig: StoreWechatConfig | null;
  wechatLoading: boolean;
  onStoreChange: (storeId: string) => void;
  onSubmit: (values: any) => Promise<void>;
}

// ===================== ImageTab =====================

export interface ImageTabProps extends BaseTabProps {
  imageConfig: ImageConfig | null;
  onSubmit: (values: any) => Promise<void>;
}

// ===================== SmsTab =====================

export interface SmsTabProps extends BaseTabProps {
  smsConfig: SmsConfig | null;
  onSubmit: (values: any) => Promise<void>;
}

// ===================== SecurityTab =====================

export interface SecurityTabProps extends BaseTabProps {
  securityConfig: SecurityConfig | null;
  onSubmit: (values: any) => Promise<void>;
}

// ===================== SourceReleaseTab =====================

export interface SourceReleaseTabProps extends BaseTabProps {
  sourceReleaseConfig: SourceReleaseConfig | null;
  onSubmit: (values: any) => Promise<void>;
}
