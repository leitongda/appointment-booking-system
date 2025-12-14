export interface Doctor {
  id: string;
  userId?: string;
  storeId?: string;
  storeName?: string;
  departmentId: string;
  departmentName?: string;
  
  // 基础信息
  name: string;
  username?: string;
  phone?: string;
  gender: number;
  avatar?: string;
  banner?: string;
  title?: string;
  yearsOfExperience: number;
  
  // 资质信息
  education?: string;
  graduateSchool?: string;
  licenseNumber?: string;
  licenseImage?: string;
  honors?: string;
  
  // 坐诊设置
  scheduleDesc?: string;
  maxDailyAppointments: number;
  onlineConsultEnabled: number;
  onlineConsultFee: number;
  registrationFee: number;
  
  // 展示设置
  pageStyle: number;
  promoVideo?: string;
  tags?: string;
  specialty?: string;
  introduction?: string;
  
  // 其他设置
  isRecommended: number;
  sortOrder: number;
  status: number;
  
  // 诊费设置
  useFeeTemplate: number;
  
  createdAt: string;
  updatedAt: string;
}

export interface DoctorListItem {
  id: string;
  name: string;
  avatar?: string;
  banner?: string;
  title?: string;
  gender: number;
  storeId?: string;
  storeName?: string;
  departmentId: string;
  departmentName?: string;
  specialty?: string;
  registrationFee: number;
  isRecommended: number;
  tags?: string;
  pageStyle: number;
}
