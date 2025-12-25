/**
 * 诊费类型
 */
export interface ConsultationFeeType {
  id: string;
  storeId?: string;  // 门店ID，null 表示全局类型
  storeName?: string;  // 门店名称
  name: string;
  code?: string;
  description?: string;
  sortOrder: number;
  status: number;
  isGlobal?: boolean;  // 是否为全局类型
  createdAt: string;
  updatedAt: string;
}

/**
 * 创建诊费类型请求
 */
export interface ConsultationFeeTypeCreate {
  storeId?: string;  // 门店ID，不传表示创建全局类型
  name: string;
  code?: string;
  description?: string;
  sortOrder?: number;
  status?: number;
}

/**
 * 更新诊费类型请求
 */
export interface ConsultationFeeTypeUpdate {
  storeId?: string;
  name?: string;
  code?: string;
  description?: string;
  sortOrder?: number;
  status?: number;
}

/**
 * 诊费模板（全局默认配置）
 */
export interface ConsultationFeeTemplate {
  id: string;
  feeTypeId: string;
  feeTypeName?: string;
  feeTypeCode?: string;
  initialFee: number;
  followUpFee: number;
  status: number;
  createdAt: string;
  updatedAt: string;
}

/**
 * 带诊费类型信息的模板（用于列表展示）
 */
export interface ConsultationFeeTemplateWithType {
  id?: string;
  feeTypeId: string;
  feeTypeName: string;
  feeTypeCode?: string;
  initialFee: number;
  followUpFee: number;
  status: number;
}

/**
 * 门店诊费模板
 */
export interface StoreFeeTemplate {
  id: string;
  storeId: string;
  storeName?: string;
  feeTypeId: string;
  feeTypeName?: string;
  feeTypeCode?: string;
  initialFee: number;
  followUpFee: number;
  status: number;
  createdAt: string;
  updatedAt: string;
}

/**
 * 门店诊费模板项（用于批量保存）
 */
export interface StoreFeeTemplateItem {
  feeTypeId: string;
  feeTypeName?: string;
  feeTypeCode?: string;
  initialFee: number;
  followUpFee: number;
}

/**
 * 批量保存门店诊费模板请求
 */
export interface StoreFeeTemplateBatchCreate {
  storeId: string;
  templates: StoreFeeTemplateItem[];
}

/**
 * 带诊费类型信息的门店模板响应（用于列表展示）
 */
export interface StoreFeeTemplateWithType {
  id?: string;
  storeId?: string;
  feeTypeId: string;
  feeTypeName: string;
  feeTypeCode?: string;
  initialFee: number;
  followUpFee: number;
  globalInitialFee?: number;  // 全局模板的初诊金额（用于参考）
  globalFollowUpFee?: number;  // 全局模板的复诊金额（用于参考）
  status: number;
  isGlobalType: boolean;  // 是否为全局类型
}

/**
 * 一键带入模板请求
 */
export interface ApplyTemplateRequest {
  storeId: string;
  departmentId: string;
}

/**
 * 医生诊费配置
 */
export interface DoctorConsultationFee {
  id: string;
  doctorId: string;
  storeId: string;
  storeName?: string;
  departmentId: string;
  departmentName?: string;
  feeTypeId: string;
  feeTypeName?: string;
  feeTypeCode?: string;
  initialFee: number;
  followUpFee: number;
  status: number;
  createdAt: string;
  updatedAt: string;
}

/**
 * 单个诊费类型的金额配置（用于批量保存）
 */
export interface DoctorConsultationFeeItem {
  feeTypeId: string;
  feeTypeName?: string;
  feeTypeCode?: string;
  initialFee: number;
  followUpFee: number;
}

/**
 * 批量保存医生诊费配置的请求
 */
export interface DoctorConsultationFeeBatchCreate {
  doctorId: string;
  storeId: string;
  departmentId: string;
  fees: DoctorConsultationFeeItem[];
}

/**
 * 医生诊费设置响应（包含是否使用模板）
 */
export interface DoctorFeeSettingResponse {
  doctorId: string;
  doctorName: string;
  useFeeTemplate: number;
  fees: DoctorConsultationFee[];
}

/**
 * 门店-科室下的诊费配置分组
 */
export interface StoreDepartmentFeeGroup {
  storeId: string;
  storeName: string;
  departmentId: string;
  departmentName: string;
  fees: DoctorConsultationFeeItem[];
}
