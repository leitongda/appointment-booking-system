export interface Department {
  id: string;
  name: string;
  parentId?: string;
  description?: string;
  sortOrder: number;
  isHot: number;
  status: number;
  createdAt: string;
  updatedAt: string;
  
  // 基础配置
  storeId?: string;
  storeName?: string;
  tag?: string;
  enableBanner: number;
  enableIntro: number;
  isFinal: number;
  isRecommended: number;
  
  // 图片资源
  bannerImage?: string;
  icon?: string;
  introImages?: string;
  
  // 详情内容
  introContent?: string;
  features?: string;
  appointmentNotice?: string;
  
  // 联系信息
  phone?: string;
  location?: string;
  workingHours?: string;
}

export interface DepartmentTreeNode {
  id: string;
  name: string;
  parentId?: string;
  children: DepartmentTreeNode[];
}
