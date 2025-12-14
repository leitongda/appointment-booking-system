/**
 * 诊费类型
 */
export interface ConsultationFeeType {
  id: string;
  name: string;
  code?: string;
  description?: string;
  sortOrder: number;
  status: number;
  createdAt: string;
  updatedAt: string;
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
