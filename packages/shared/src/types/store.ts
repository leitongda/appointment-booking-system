export interface Store {
  id: string;
  name: string;
  code?: string;
  address?: string;
  province?: string;
  city?: string;
  district?: string;
  latitude?: string;
  longitude?: string;
  phone?: string;
  contactPerson?: string;
  description?: string;
  openingTime?: string;
  closingTime?: string;
  workingDays?: string;
  image?: string;
  logo?: string;
  password?: string;
  email?: string;
  themeStyle?: string;
  sortOrder: number;
  status: number;
  departmentCount?: number;
  createdAt: string;
  updatedAt: string;
}

export interface StoreDepartment {
  id: string;
  storeId: string;
  departmentId: string;
  departmentName?: string;
  floor?: string;
  room?: string;
  status: number;
  createdAt: string;
}
