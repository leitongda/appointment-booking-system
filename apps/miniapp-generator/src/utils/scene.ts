/**
 * 海报小程序码 scene 编解码契约
 *
 * 微信 getwxacodeunlimit 的 scene 上限为 32 个可见字符，而医生 ID 是
 * 36 位带连字符的 UUID：`d=<doctorId>` 共 38 字符必然超限（后端
 * Query(max_length=32) 直接 422）。约定 scene 为「医生 UUID 去掉连字符
 * 后的 32 位十六进制」，恰好 32 字符；落地页用 decodeDoctorScene 还原。
 */

/** 校验并还原为标准 36 位小写 UUID；非法返回空串 */
const compactHexToUuid = (compact: string): string => {
  if (!/^[0-9a-fA-F]{32}$/.test(compact)) return '';
  return (
    `${compact.slice(0, 8)}-${compact.slice(8, 12)}-` +
    `${compact.slice(12, 16)}-${compact.slice(16, 20)}-${compact.slice(20)}`
  ).toLowerCase();
};

/** 医生 UUID → 32 位十六进制 scene（非法/超长返回空串，调用方走占位降级） */
export const encodeDoctorScene = (doctorId?: string | null): string => {
  const compact = (doctorId || '').replace(/-/g, '');
  return /^[0-9a-fA-F]{32}$/.test(compact) ? compact.toLowerCase() : '';
};

/** scene（或任意入参）→ 标准 36 位医生 UUID；无法识别时返回空串 */
export const decodeDoctorScene = (raw?: string | null): string => {
  if (!raw) return '';
  let scene = raw;
  try {
    // 微信扫码进入时 scene 可能带 URL 编码
    scene = decodeURIComponent(raw);
  } catch {
    // 非法百分号编码时保留原值继续解析
  }
  // 兼容 d=<uuid> / d.<hex32> 前缀与裸值
  const value = scene.trim().replace(/^[dD][=.]/, '');
  return compactHexToUuid(value.replace(/-/g, ''));
};

/** 扫码落地页参数解析：优先显式 id（站内跳转），其次 scene（扫码进入） */
export const resolveDoctorIdFromParams = (
  params?: Record<string, string | undefined> | null,
): string => {
  if (!params) return '';
  return params.id || decodeDoctorScene(params.scene);
};
