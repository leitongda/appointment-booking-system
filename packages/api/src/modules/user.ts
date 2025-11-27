import request from '../request';
import type { User, Patient } from '@hospital/shared';

export interface PatientCreateData {
  name: string;
  phone: string;
  idCard?: string;
  gender?: number;
  relationship?: string;
  isDefault?: boolean;
}

export const userApi = {
  getProfile: (): Promise<User> => {
    return request.get('/users/profile');
  },

  updateProfile: (data: Partial<User>): Promise<User> => {
    return request.put('/users/profile', data);
  },

  getPatients: (): Promise<Patient[]> => {
    return request.get('/users/patients');
  },

  addPatient: (data: PatientCreateData): Promise<Patient> => {
    return request.post('/users/patients', data);
  },

  updatePatient: (id: string, data: Partial<PatientCreateData>): Promise<Patient> => {
    return request.put(`/users/patients/${id}`, data);
  },

  deletePatient: (id: string): Promise<void> => {
    return request.delete(`/users/patients/${id}`);
  },
};
