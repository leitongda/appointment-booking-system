/**
 * 数据验证工具函数
 *
 * ────────────────────────────────────────────────────────────────────────────
 * 与 @hospital/shared 的对齐说明（改动前必读）
 * ────────────────────────────────────────────────────────────────────────────
 * 本文件刻意**不导入** `@hospital/shared`（保持小程序独立发布），但其中以下逻辑
 * 在 `packages/shared` 内有同名实现，改动必须双侧同步评估，避免校验漂移：
 *
 * | 逻辑                 | 本文件实现                    | shared 对应实现                                |
 * | -------------------- | ----------------------------- | ---------------------------------------------- |
 * | 手机号正则           | `validatePhone`               | `REGEX.PHONE` (`constants/common.ts`)          |
 * | 身份证格式正则       | `validateIdCard` 内 idCardRegex| `REGEX.ID_CARD` (`constants/common.ts`)        |
 * | 身份证校验码算法     | `validateIdCard` ISO 7064 MOD 11-2 | shared 仅做格式正则，**未计算校验码**     |
 *
 * 对齐结论（核对日期 2026-07-01）：
 * 1. **手机号正则**：本文件 `/^1[3-9]\d{9}$/` 与 `REGEX.PHONE` **完全一致**。
 * 2. **身份证校验码算法**：本文件采用国标 GB 11643-1999 / ISO 7064 MOD 11-2
 *    （加权因子 `[7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2]`，`sum % 11` 索引
 *    `['1','0','X','9','8','7','6','5','4','3','2']`，末位 X 统一大写比较），
 *    这是**标准实现**；shared 当前**未提供**校验码算法（仅 18 位格式正则），
 *    因此本文件算法**不与 shared 冲突**，反而更严格。
 *    若未来 shared 新增校验码算法，必须以 GB 11643-1999 为准保持一致。
 * 3. **身份证格式正则**：本文件兼容 15 位 + 18 位（`admin` 端 `PATTERNS.ID_CARD`
 *    同款宽松正则）；shared `REGEX.ID_CARD` 仅匹配 18 位且校验出生日期段，更严格。
 *    小程序端出于兼容老人/历史 15 位号源，保留宽松正则 + 校验码双重校验。
 *
 * 红线：任何对加权因子 / `sum % 11` / 末位 X 处理的修改，都意味着与国标或 shared
 * 产生漂移，PR 必须同步更新 shared 侧并说明。
 * ────────────────────────────────────────────────────────────────────────────
 */

/**
 * 验证手机号
 *
 * 正则 `/^1[3-9]\d{9}$/` 已与 `@hospital/shared` 的 `REGEX.PHONE`
 * （`packages/shared/src/constants/common.ts`）对齐，完全一致。
 * 改动需同步 shared。
 *
 * @param phone 手机号
 */
export function validatePhone(phone: string): boolean {
  const phoneRegex = /^1[3-9]\d{9}$/;
  return phoneRegex.test(phone);
}

/**
 * 验证身份证号
 *
 * 校验流程（已与 `@hospital/shared` 核对，见文件顶部对齐说明）：
 * 1. 格式正则：兼容 15 位 / 18 位（与 admin `PATTERNS.ID_CARD` 同款）。
 * 2. 18 位号码额外执行 GB 11643-1999 / ISO 7064 MOD 11-2 校验码算法
 *    （加权因子 + mod 11 + 末位 X 大写比较）。shared 当前仅做格式正则、
 *    未计算校验码；本实现更严格，且与国标一致，不与 shared 冲突。
 *
 * 校验码算法：加权因子 `[7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2]`，
 * `checkCodes[sum % 11]` 索引表 `['1','0','X','9','8','7','6','5','4','3','2']`，
 * 末位统一 `toUpperCase()` 后比较（X 大写）。
 *
 * @param idCard 身份证号
 */
export function validateIdCard(idCard: string): boolean {
  // 15位或18位身份证号（末位可能是数字或 X/x）
  const idCardRegex = /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/;

  if (!idCardRegex.test(idCard)) {
    return false;
  }

  // 18位身份证校验码（GB 11643-1999 / ISO 7064 MOD 11-2）
  if (idCard.length === 18) {
    // 加权因子（与 shared 对齐：shared 暂未实现，此处为标准国标因子）
    const factors = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2];
    // sum % 11 对应的校验码映射表（索引 0~10）
    const checkCodes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2'];

    let sum = 0;
    for (let i = 0; i < 17; i++) {
      sum += parseInt(idCard[i], 10) * factors[i];
    }

    const checkCode = checkCodes[sum % 11];
    // 末位 X 统一大写比较
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
