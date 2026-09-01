import type { Doctor as SharedDoctor, Patient as SharedPatient, DepartmentTreeNode as SharedDepartmentTreeNode } from '@hospital/shared';
import type { Banner as ApiBanner } from '@hospital/api';

declare module '@hospital/shared' {
  interface Doctor extends SharedDoctor {
    rating?: number;
    academicTitle?: string;
    services?: Array<{ name: string; price: number | string }>;
    highlights?: string[];
  }

  interface Patient extends SharedPatient {
    avatar?: string;
  }

  interface DepartmentTreeNode extends SharedDepartmentTreeNode {
    description?: string;
  }
}

declare module '@hospital/api' {
  interface Banner extends ApiBanner {
    description?: string;
  }
}
