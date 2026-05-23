import { request } from '../request';
import type { PageResult } from '@hospital/shared';

// ========== Types ==========

export interface FollowUpPlanStep {
  id: string;
  planId: string;
  stepOrder: number;
  name: string;
  daysAfterVisit: number;
  description?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface FollowUpPlan {
  id: string;
  name: string;
  description?: string;
  departmentId?: string;
  departmentName?: string;
  diagnosisCode?: string;
  diagnosisName?: string;
  status?: number;
  steps: FollowUpPlanStep[];
  createdAt?: string;
  updatedAt?: string;
}

export interface FollowUpPlanListItem {
  id: string;
  name: string;
  departmentName?: string;
  diagnosisName?: string;
  status?: number;
  stepCount?: number;
  createdAt?: string;
}

export interface FollowUpPlanCreateData {
  name: string;
  description?: string;
  departmentId?: string;
  diagnosisCode?: string;
  diagnosisName?: string;
  steps: { stepOrder: number; name: string; daysAfterVisit: number; description?: string }[];
}

export interface FollowUpPlanUpdateData {
  name?: string;
  description?: string;
  departmentId?: string;
  diagnosisCode?: string;
  diagnosisName?: string;
  status?: number;
}

export interface FollowUpTask {
  id: string;
  taskNo?: string;
  patientId: string;
  patientName?: string;
  doctorId: string;
  doctorName?: string;
  departmentId: string;
  departmentName?: string;
  appointmentId?: string;
  medicalRecordId?: string;
  planId?: string;
  planName?: string;
  stepOrder?: number;
  scheduledDate?: string;
  status?: string;
  completedAt?: string;
  completedBy?: string;
  skipReason?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface FollowUpTaskListItem {
  id: string;
  taskNo?: string;
  patientName?: string;
  doctorName?: string;
  departmentName?: string;
  scheduledDate?: string;
  status?: string;
  planName?: string;
  stepOrder?: number;
  createdAt?: string;
}

export interface FollowUpTaskCreateData {
  patientId: string;
  doctorId: string;
  departmentId: string;
  appointmentId?: string;
  medicalRecordId?: string;
  scheduledDate: string;
  description?: string;
}

export interface FollowUpTaskGenerateData {
  patientId: string;
  doctorId: string;
  departmentId: string;
  planId: string;
  appointmentId?: string;
  medicalRecordId?: string;
  baseDate?: string;
}

export interface FollowUpRecord {
  id: string;
  taskId?: string;
  patientId: string;
  patientName?: string;
  doctorId: string;
  doctorName?: string;
  appointmentId?: string;
  medicalRecordId?: string;
  followUpDate?: string;
  content?: string;
  patientCondition?: string;
  nextAction?: string;
  nextFollowUpDate?: string;
  attachments?: string[];
  createdAt?: string;
  updatedAt?: string;
}

export interface FollowUpRecordListItem {
  id: string;
  patientName?: string;
  doctorName?: string;
  followUpDate?: string;
  content?: string;
  patientCondition?: string;
  taskId?: string;
  createdAt?: string;
}

export interface FollowUpRecordCreateData {
  taskId?: string;
  patientId: string;
  doctorId: string;
  appointmentId?: string;
  medicalRecordId?: string;
  followUpDate?: string;
  content: string;
  patientCondition?: string;
  nextAction?: string;
  nextFollowUpDate?: string;
  attachments?: string[];
}

export interface FollowUpRecordUpdateData {
  content?: string;
  patientCondition?: string;
  nextAction?: string;
  nextFollowUpDate?: string;
  attachments?: string[];
}

export type { PageResult } from '@hospital/shared';

const PREFIX = '/follow-up';

export const followUpApi = {
  // ========== Plans ==========

  getPlanList: (params?: { departmentId?: string; diagnosisCode?: string; status?: number; keyword?: string; page?: number; pageSize?: number }): Promise<PageResult<FollowUpPlanListItem>> => {
    return request.get(`${PREFIX}/plans`, { params });
  },

  getPlanDetail: (id: string): Promise<FollowUpPlan> => {
    return request.get(`${PREFIX}/plans/${id}`);
  },

  createPlan: (data: FollowUpPlanCreateData): Promise<FollowUpPlan> => {
    return request.post(`${PREFIX}/plans`, data);
  },

  updatePlan: (id: string, data: FollowUpPlanUpdateData): Promise<FollowUpPlan> => {
    return request.put(`${PREFIX}/plans/${id}`, data);
  },

  updatePlanSteps: (id: string, steps: FollowUpPlanCreateData['steps']): Promise<FollowUpPlan> => {
    return request.put(`${PREFIX}/plans/${id}/steps`, { steps });
  },

  deletePlan: (id: string): Promise<void> => {
    return request.delete(`${PREFIX}/plans/${id}`);
  },

  // ========== Tasks ==========

  getTaskList: (params?: { doctorId?: string; patientId?: string; departmentId?: string; status?: string; startDate?: string; endDate?: string; keyword?: string; page?: number; pageSize?: number }): Promise<PageResult<FollowUpTaskListItem>> => {
    return request.get(`${PREFIX}/tasks`, { params });
  },

  getMyTasks: (params?: { status?: string; page?: number; pageSize?: number }): Promise<PageResult<FollowUpTaskListItem>> => {
    return request.get(`${PREFIX}/tasks/my`, { params });
  },

  /** 患者端专用：获取当前患者的随访任务（从 token 自动解析，可传 patientId 查看家庭成员数据） */
  getMyPatientTasks: (params?: { patientId?: string; status?: string; page?: number; pageSize?: number }): Promise<PageResult<FollowUpTaskListItem>> => {
    return request.get(`${PREFIX}/tasks/my-patient`, { params });
  },

  getOverdueTasks: (params?: { page?: number; pageSize?: number }): Promise<PageResult<FollowUpTaskListItem>> => {
    return request.get(`${PREFIX}/tasks/overdue`, { params });
  },

  getPatientTasks: (patientId: string, params?: { page?: number; pageSize?: number }): Promise<PageResult<FollowUpTaskListItem>> => {
    return request.get(`${PREFIX}/tasks/patient/${patientId}`, { params });
  },

  getTaskDetail: (id: string): Promise<FollowUpTask> => {
    return request.get(`${PREFIX}/tasks/${id}`);
  },

  createTask: (data: FollowUpTaskCreateData): Promise<FollowUpTask> => {
    return request.post(`${PREFIX}/tasks`, data);
  },

  generateTasks: (data: FollowUpTaskGenerateData): Promise<FollowUpTask[]> => {
    return request.post(`${PREFIX}/tasks/generate`, data);
  },

  completeTask: (id: string): Promise<FollowUpTask> => {
    return request.patch(`${PREFIX}/tasks/${id}/complete`);
  },

  skipTask: (id: string, reason: string): Promise<FollowUpTask> => {
    return request.patch(`${PREFIX}/tasks/${id}/skip`, { reason });
  },

  deleteTask: (id: string): Promise<void> => {
    return request.delete(`${PREFIX}/tasks/${id}`);
  },

  // ========== Records ==========

  getRecordList: (params?: { doctorId?: string; patientId?: string; taskId?: string; startDate?: string; endDate?: string; keyword?: string; page?: number; pageSize?: number }): Promise<PageResult<FollowUpRecordListItem>> => {
    return request.get(`${PREFIX}/records`, { params });
  },

  getPatientRecords: (patientId: string, params?: { page?: number; pageSize?: number }): Promise<PageResult<FollowUpRecordListItem>> => {
    return request.get(`${PREFIX}/records/patient/${patientId}`, { params });
  },

  /** 患者端专用：获取当前患者的随访记录（从 token 自动解析，可传 patientId 查看家庭成员数据） */
  getMyPatientRecords: (params?: { patientId?: string; page?: number; pageSize?: number }): Promise<PageResult<FollowUpRecordListItem>> => {
    return request.get(`${PREFIX}/records/my-patient`, { params });
  },

  getTaskRecords: (taskId: string): Promise<FollowUpRecord[]> => {
    return request.get(`${PREFIX}/records/task/${taskId}`);
  },

  getRecordDetail: (id: string): Promise<FollowUpRecord> => {
    return request.get(`${PREFIX}/records/${id}`);
  },

  createRecord: (data: FollowUpRecordCreateData): Promise<FollowUpRecord> => {
    return request.post(`${PREFIX}/records`, data);
  },

  updateRecord: (id: string, data: FollowUpRecordUpdateData): Promise<FollowUpRecord> => {
    return request.put(`${PREFIX}/records/${id}`, data);
  },

  deleteRecord: (id: string): Promise<void> => {
    return request.delete(`${PREFIX}/records/${id}`);
  },

  // ========== Statistics ==========

  getStatistics: (params?: { startDate?: string; endDate?: string }): Promise<FollowUpStatistics> => {
    return request.get(`${PREFIX}/statistics`, { params });
  },
};

export interface FollowUpStatistics {
  total: number;
  completed: number;
  overdue: number;
  skipped: number;
  pending: number;
  completionRate: number;
  overdueRate: number;
  doctorRanking: {
    doctorId: string;
    doctorName: string;
    total: number;
    completed: number;
    rate: number;
  }[];
}

// ========== Self Reports (患者自报告) ==========

export interface SelfReportCreateData {
  taskId?: string;
  reportDate?: string;
  systolicBp?: number;
  diastolicBp?: number;
  bloodGlucose?: number;
  heartRate?: number;
  temperature?: number;
  symptoms?: string;
  patientCondition?: 'improved' | 'stable' | 'worsened';
  notes?: string;
  attachments?: string[];
}

export interface SelfReportListItem {
  id: string;
  taskId?: string;
  patientName?: string;
  reportDate?: string;
  systolicBp?: number;
  diastolicBp?: number;
  bloodGlucose?: number;
  symptoms?: string;
  patientCondition?: string;
  status?: string;
  createdAt?: string;
}

export interface SelfReportDetail extends SelfReportListItem {
  patientId: string;
  heartRate?: number;
  temperature?: number;
  notes?: string;
  attachments?: string[];
  reviewedAt?: string;
  reviewedBy?: string;
}

export const selfReportApi = {
  /** 创建自报告（患者端，从 token 解析 patient_id） */
  create: (data: SelfReportCreateData): Promise<SelfReportDetail> => {
    return request.post(`${PREFIX}/self-reports`, data);
  },

  /** 获取当前患者的自报告列表 */
  getMyList: (params?: { taskId?: string; page?: number; pageSize?: number }): Promise<PageResult<SelfReportListItem>> => {
    return request.get(`${PREFIX}/self-reports/my`, { params });
  },

  /** 获取自报告详情 */
  getDetail: (id: string): Promise<SelfReportDetail> => {
    return request.get(`${PREFIX}/self-reports/${id}`);
  },

  /** 获取任务关联的自报告 */
  getByTask: (taskId: string): Promise<SelfReportListItem[]> => {
    return request.get(`${PREFIX}/self-reports/task/${taskId}`);
  },

  /** 自报告列表（管理端） */
  getList: (params?: { patientId?: string; taskId?: string; status?: string; page?: number; pageSize?: number }): Promise<PageResult<SelfReportListItem>> => {
    return request.get(`${PREFIX}/self-reports`, { params });
  },

  /** 审核自报告（医生端） */
  review: (id: string): Promise<SelfReportDetail> => {
    return request.patch(`${PREFIX}/self-reports/${id}/review`);
  },
};
