/**
 * 用户角色
 */
export const USER_ROLE = {
  ADMIN: 'ADMIN',       // 管理员
  DOCTOR: 'DOCTOR',     // 医生
  PATIENT: 'PATIENT',   // 患者
} as const;

export const USER_ROLE_MAP: Record<string, string> = {
  [USER_ROLE.ADMIN]: '管理员',
  [USER_ROLE.DOCTOR]: '医生',
  [USER_ROLE.PATIENT]: '患者',
};

/**
 * 性别
 */
export const GENDER = {
  UNKNOWN: 0,  // 未知
  MALE: 1,     // 男
  FEMALE: 2,   // 女
} as const;

export const GENDER_MAP: Record<number, string> = {
  [GENDER.UNKNOWN]: '未知',
  [GENDER.MALE]: '男',
  [GENDER.FEMALE]: '女',
};

export const GENDER_OPTIONS = [
  { label: GENDER_MAP[GENDER.UNKNOWN], value: GENDER.UNKNOWN },
  { label: GENDER_MAP[GENDER.MALE], value: GENDER.MALE },
  { label: GENDER_MAP[GENDER.FEMALE], value: GENDER.FEMALE },
];

/**
 * 医生职称
 */
export const DOCTOR_TITLE = {
  CHIEF: '主任医师',
  ASSOCIATE_CHIEF: '副主任医师',
  ATTENDING: '主治医师',
  RESIDENT: '住院医师',
} as const;

export const DOCTOR_TITLES = Object.values(DOCTOR_TITLE);

export const DOCTOR_TITLE_MAP: Record<string, string> = {
  '主任医师': '主任医师',
  '副主任医师': '副主任医师',
  '主治医师': '主治医师',
  '住院医师': '住院医师',
};

/**
 * 就诊人关系
 */
export const PATIENT_RELATIONSHIP = {
  SELF: '本人',
  PARENT: '父母',
  CHILD: '子女',
  SPOUSE: '配偶',
  OTHER: '其他',
} as const;

export const PATIENT_RELATIONSHIPS = Object.values(PATIENT_RELATIONSHIP);
