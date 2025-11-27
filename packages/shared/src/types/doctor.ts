export interface Doctor {
  id: string;
  userId?: string;
  departmentId: string;
  departmentName?: string;
  name: string;
  phone?: string;
  avatar?: string;
  title?: string;
  specialty?: string;
  introduction?: string;
  registrationFee: number;
  isRecommended: number;
  sortOrder: number;
  status: number;
  createdAt: string;
  updatedAt: string;
}

export interface DoctorListItem {
  id: string;
  name: string;
  avatar?: string;
  title?: string;
  departmentId: string;
  departmentName?: string;
  specialty?: string;
  registrationFee: number;
  isRecommended: number;
}
