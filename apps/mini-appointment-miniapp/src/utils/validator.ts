/**
 * 数据验证工具函数
 */

/**
 * 验证手机号
 * @param phone 手机号
 */
export function validatePhone(phone: string): boolean {
  const phoneRegex = /^1[3-9]\d{9}$/;
  return phoneRegex.test(phone);
}

/**
 * 验证身份证号
 * @param idCard 身份证号
 */
export function validateIdCard(idCard: string): boolean {
  // 15位或18位身份证号
  const idCardRegex = /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/;
  
  if (!idCardRegex.test(idCard)) {
    return false;
  }

  // 18位身份证校验
  if (idCard.length === 18) {
    const factors = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2];
    const checkCodes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2'];
    
    let sum = 0;
    for (let i = 0; i < 17; i++) {
      sum += parseInt(idCard[i]) * factors[i];
    }
    
    const checkCode = checkCodes[sum % 11];
    return idCard[17].toUpperCase() === checkCode;
  }

  return true;
}

/**
 * 验证姓名
 * @param name 姓名
 */
export function validateName(name: string): boolean {
  // 2-20个字符，支持中文、英文、·
  const nameRegex = /^[\u4e00-\u9fa5a-zA-Z·]{2,20}$/;
  return nameRegex.test(name);
}

/**
 * 验证邮箱
 * @param email 邮箱
 */
export function validateEmail(email: string): boolean {
  const emailRegex = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$/;
  return emailRegex.test(email);
}

/**
 * 验证密码强度
 * @param password 密码
 * @returns 强度等级：0-弱，1-中，2-强
 */
export function validatePasswordStrength(password: string): number {
  if (password.length < 6) {
    return 0;
  }

  let strength = 0;

  // 包含小写字母
  if (/[a-z]/.test(password)) {
    strength++;
  }

  // 包含大写字母
  if (/[A-Z]/.test(password)) {
    strength++;
  }

  // 包含数字
  if (/\d/.test(password)) {
    strength++;
  }

  // 包含特殊字符
  if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
    strength++;
  }

  // 长度大于8
  if (password.length >= 8) {
    strength++;
  }

  if (strength <= 2) {
    return 0; // 弱
  } else if (strength <= 4) {
    return 1; // 中
  } else {
    return 2; // 强
  }
}

/**
 * 从身份证号中提取生日
 * @param idCard 身份证号
 */
export function getBirthdayFromIdCard(idCard: string): string | null {
  if (!validateIdCard(idCard)) {
    return null;
  }

  let birthday = '';
  
  if (idCard.length === 15) {
    birthday = `19${idCard.substr(6, 2)}-${idCard.substr(8, 2)}-${idCard.substr(10, 2)}`;
  } else if (idCard.length === 18) {
    birthday = `${idCard.substr(6, 4)}-${idCard.substr(10, 2)}-${idCard.substr(12, 2)}`;
  }

  return birthday;
}

/**
 * 从身份证号中提取性别
 * @param idCard 身份证号
 * @returns 1-男，2-女
 */
export function getGenderFromIdCard(idCard: string): number | null {
  if (!validateIdCard(idCard)) {
    return null;
  }

  let genderCode = '';
  
  if (idCard.length === 15) {
    genderCode = idCard.substr(14, 1);
  } else if (idCard.length === 18) {
    genderCode = idCard.substr(16, 1);
  }

  return parseInt(genderCode) % 2 === 0 ? 2 : 1;
}

/**
 * 计算年龄
 * @param birthday 生日，格式 'YYYY-MM-DD'
 */
export function calculateAge(birthday: string): number {
  const birthDate = new Date(birthday);
  const today = new Date();
  
  let age = today.getFullYear() - birthDate.getFullYear();
  const monthDiff = today.getMonth() - birthDate.getMonth();
  
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
    age--;
  }

  return age;
}

/**
 * 脱敏手机号
 * @param phone 手机号
 */
export function maskPhone(phone: string): string {
  if (!phone || phone.length !== 11) {
    return phone;
  }
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2');
}

/**
 * 脱敏身份证号
 * @param idCard 身份证号
 */
export function maskIdCard(idCard: string): string {
  if (!idCard || (idCard.length !== 15 && idCard.length !== 18)) {
    return idCard;
  }
  return idCard.replace(/(\d{6})\d+(\d{4})/, '$1********$2');
}

/**
 * 脱敏姓名
 * @param name 姓名
 */
export function maskName(name: string): string {
  if (!name || name.length < 2) {
    return name;
  }
  if (name.length === 2) {
    return name[0] + '*';
  }
  return name[0] + '*'.repeat(name.length - 2) + name[name.length - 1];
}
