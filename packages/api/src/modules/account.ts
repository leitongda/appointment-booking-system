import { request } from '../request';
import type { AccountInfo } from './auth';

const PREFIX = '/accounts';

export const accountApi = {
  /**
   * 获取当前登录账号（统一视图）
   */
  getMe: (): Promise<AccountInfo> => {
    return request.get(`${PREFIX}/me`);
  },

  /**
   * 统一账号修改密码（admin/doctor/user 通用）
   */
  changePassword: (data: { oldPassword: string; newPassword: string }): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/me/change-password`, {
      old_password: data.oldPassword,
      new_password: data.newPassword,
    });
  },

  /**
   * 发送统一账号邮箱验证码（绑定/解绑/换绑）
   * 不传 email 时发送到当前绑定邮箱
   */
  sendEmailCode: (email?: string): Promise<{ message: string; code?: string }> => {
    const payload = email ? { email, code_type: 'bind' } : { code_type: 'bind' };
    return request.post(`${PREFIX}/me/email/send-code`, payload);
  },

  /**
   * 统一账号绑定邮箱
   */
  emailBind: (data: { email: string; code: string }): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/me/email/bind`, {
      email: data.email,
      code: data.code,
    });
  },

  /**
   * 统一账号解绑邮箱
   */
  emailUnbind: (data: { code: string }): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/me/email/unbind`, { code: data.code });
  },

  /**
   * 统一账号换绑邮箱
   */
  emailChange: (data: { newEmail: string; newEmailCode: string; oldEmailCode: string }): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/me/email/change`, {
      new_email: data.newEmail,
      new_email_code: data.newEmailCode,
      old_email_code: data.oldEmailCode,
    });
  },
};
