import { request } from '../request';

export interface MedicalRecord {
  id: string;
  recordNo: string;
  appointmentId: string;
  patientId: string;
  patientName?: string;
  patientPhone?: string;
  patientGender?: number;
  doctorId: string;
  doctorName?: string;
  departmentId: string;
  departmentName?: string;
  chiefComplaint?: string;
  presentIllness?: string;
  pastHistory?: string;
  allergyHistory?: string;
  familyHistory?: string;
  medicationHistory?: string;
  physicalExam?: string;
  auxiliaryExam?: string;
  diagnosis: string;
  treatment?: string;
  prescription?: string;
  advice?: string;
  totalFee?: number;
  status: number;
  visitDate?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface MedicalRecordListItem {
  id: string;
  recordNo: string;
  patientName?: string;
  doctorName?: string;
  departmentName?: string;
  diagnosis: string;
  visitDate?: string;
  status: number;
  createdAt: string;
}

export interface MedicalRecordListParams {
  doctorId?: string;
  patientId?: string;
  departmentId?: string;
  startDate?: string;
  endDate?: string;
  status?: number;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

export interface MedicalRecordCreateData {
  appointmentId: string;
  chiefComplaint: string;
  presentIllness?: string;
  pastHistory?: string;
  allergyHistory?: string;
  familyHistory?: string;
  medicationHistory?: string;
  physicalExam?: string;
  auxiliaryExam?: string;
  diagnosis: string;
  treatment?: string;
  prescription?: string;
  advice?: string;
  totalFee?: number;
  status?: number;
}

export interface MedicalRecordUpdateData {
  chiefComplaint?: string;
  presentIllness?: string;
  pastHistory?: string;
  allergyHistory?: string;
  familyHistory?: string;
  medicationHistory?: string;
  physicalExam?: string;
  auxiliaryExam?: string;
  diagnosis?: string;
  treatment?: string;
  prescription?: string;
  advice?: string;
  totalFee?: number;
  status?: number;
}

export interface PageResult<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
}

const PREFIX = '/medical-records';

export const medicalRecordApi = {
  /**
   * 获取病历列表
   */
  getList: (params?: MedicalRecordListParams): Promise<PageResult<MedicalRecordListItem>> => {
    return request.get(PREFIX, { params });
  },

  /**
   * 获取当前医生的病历列表
   */
  getMyRecords: (params?: { page?: number; pageSize?: number }): Promise<PageResult<MedicalRecordListItem>> => {
    return request.get(`${PREFIX}/my`, { params });
  },

  /**
   * 获取患者的病历列表
   */
  getPatientRecords: (
    patientId: string,
    params?: { page?: number; pageSize?: number }
  ): Promise<PageResult<MedicalRecordListItem>> => {
    return request.get(`${PREFIX}/patient/${patientId}`, { params });
  },

  /**
   * 根据预约ID获取病历
   */
  getByAppointment: (appointmentId: string): Promise<MedicalRecord> => {
    return request.get(`${PREFIX}/appointment/${appointmentId}`);
  },

  /**
   * 获取病历详情
   */
  getDetail: (id: string): Promise<MedicalRecord> => {
    return request.get(`${PREFIX}/${id}`);
  },

  /**
   * 创建病历
   */
  create: (data: MedicalRecordCreateData): Promise<MedicalRecord> => {
    return request.post(PREFIX, data);
  },

  /**
   * 更新病历
   */
  update: (id: string, data: MedicalRecordUpdateData): Promise<MedicalRecord> => {
    return request.put(`${PREFIX}/${id}`, data);
  },

  /**
   * 删除病历
   */
  delete: (id: string): Promise<void> => {
    return request.delete(`${PREFIX}/${id}`);
  },
};

