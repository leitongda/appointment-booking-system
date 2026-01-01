/**
 * 临时挂号本地存储工具
 * 用于保存挂号流程中的临时数据
 */

const STORAGE_PREFIX = 'temp_reg_';

export interface RegistrationData {
  // 科室信息
  departmentId?: number;
  departmentName?: string;
  
  // 医生信息
  doctorId?: number;
  doctorName?: string;
  doctorTitle?: string;
  doctorAvatar?: string;
  
  // 时段信息
  scheduleId?: number;
  scheduleDate?: string;
  timeSlot?: 'morning' | 'afternoon';
  timeSlotLabel?: string;
  
  // 患者信息
  patientName?: string;
  patientPhone?: string;
  patientIdCard?: string;
  patientGender?: 'male' | 'female';
  patientAge?: number;
  
  // 挂号结果
  appointmentId?: number;
  queueNumber?: string;
  estimatedWaitTime?: number;
}

/**
 * 获取完整存储键名
 */
const getKey = (key: string) => `${STORAGE_PREFIX}${key}`;

/**
 * 保存挂号数据
 */
export const saveRegistrationData = (data: Partial<RegistrationData>) => {
  try {
    const existing = getRegistrationData();
    const updated = { ...existing, ...data };
    localStorage.setItem(getKey('data'), JSON.stringify(updated));
    return updated;
  } catch (error) {
    console.error('[Storage] Failed to save registration data:', error);
    return null;
  }
};

/**
 * 获取挂号数据
 */
export const getRegistrationData = (): RegistrationData => {
  try {
    const data = localStorage.getItem(getKey('data'));
    return data ? JSON.parse(data) : {};
  } catch (error) {
    console.error('[Storage] Failed to get registration data:', error);
    return {};
  }
};

/**
 * 清除挂号数据
 */
export const clearRegistrationData = () => {
  try {
    localStorage.removeItem(getKey('data'));
  } catch (error) {
    console.error('[Storage] Failed to clear registration data:', error);
  }
};

/**
 * 获取当前步骤
 */
export const getCurrentStep = (): number => {
  try {
    const step = localStorage.getItem(getKey('step'));
    return step ? parseInt(step, 10) : 0;
  } catch (error) {
    return 0;
  }
};

/**
 * 保存当前步骤
 */
export const setCurrentStep = (step: number) => {
  try {
    localStorage.setItem(getKey('step'), step.toString());
  } catch (error) {
    console.error('[Storage] Failed to save current step:', error);
  }
};

/**
 * 重置所有挂号状态
 */
export const resetRegistration = () => {
  clearRegistrationData();
  setCurrentStep(0);
};



