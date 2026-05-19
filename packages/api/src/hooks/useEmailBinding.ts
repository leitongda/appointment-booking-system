import { useCallback, useMemo, useState } from 'react';
import { accountApi } from '../modules/account';
import { useCountdown } from './useCountdown';

export type EmailBindingMode = 'bind' | 'unbind' | 'change';

/**
 * 邮箱绑定 Hook 所依赖的 API；默认走统一账号接口（`accountApi`）。
 * 三端可以传入相同形状的对象注入自定义实现（用于测试或兼容）。
 */
export interface EmailBindingApi {
  sendCode: (email?: string) => Promise<{ message: string; code?: string }>;
  bind: (data: { email: string; code: string }) => Promise<{ message: string }>;
  unbind: (data: { code: string }) => Promise<{ message: string }>;
  change: (data: {
    newEmail: string;
    newEmailCode: string;
    oldEmailCode: string;
  }) => Promise<{ message: string }>;
}

const defaultApi: EmailBindingApi = {
  sendCode: (email) => accountApi.sendEmailCode(email),
  bind: (data) => accountApi.emailBind(data),
  unbind: (data) => accountApi.emailUnbind(data),
  change: (data) => accountApi.emailChange(data),
};

export interface UseEmailBindingOptions {
  /** 当前已绑定邮箱（用于 unbind / change 校验） */
  currentEmail?: string | null;
  /** 提交成功后回调（绑定成功 / 解绑成功 / 换绑成功） */
  onSuccess?: (mode: EmailBindingMode) => void | Promise<void>;
  /** 错误处理回调；未传则吞掉错误 — 业务页面应当注入 message/Toast 上报 */
  onError?: (error: unknown, action: 'send-code' | 'submit') => void;
  /** 自定义底层 API（默认 `accountApi`） */
  api?: Partial<EmailBindingApi>;
}

export interface UseEmailBindingResult {
  mode: EmailBindingMode;
  open: boolean;
  submitting: boolean;
  /** 新邮箱验证码倒计时秒数（0 表示未在倒计时） */
  newCodeCountdown: number;
  /** 旧邮箱验证码倒计时秒数 */
  oldCodeCountdown: number;
  /** 是否正在发送新邮箱验证码 */
  newCodeSending: boolean;
  /** 是否正在发送旧邮箱验证码 */
  oldCodeSending: boolean;
  openModal: (mode: EmailBindingMode) => void;
  closeModal: () => void;
  /**
   * 给「新邮箱」发送验证码（绑定 / 换绑场景）。
   * @returns 是否发送成功
   */
  sendNewCode: (email: string) => Promise<boolean>;
  /**
   * 给「当前已绑定邮箱」发送验证码（解绑 / 换绑场景）。
   * @returns 是否发送成功
   */
  sendOldCode: () => Promise<boolean>;
  /** 绑定邮箱 */
  submitBind: (values: { email: string; code: string }) => Promise<boolean>;
  /** 解绑邮箱 */
  submitUnbind: (values: { code: string }) => Promise<boolean>;
  /** 换绑邮箱 */
  submitChange: (values: {
    newEmail: string;
    newEmailCode: string;
    oldEmailCode: string;
  }) => Promise<boolean>;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isValidEmail(email: string): boolean {
  return EMAIL_REGEX.test(email);
}

function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

/**
 * 邮箱绑定 / 解绑 / 换绑业务 Hook
 *
 * 统一封装三端共用的发码、倒计时、提交、错误处理与定时器清理逻辑。
 * 默认走 `accountApi.*`（`/api/v1/accounts/me/email/*`）。
 */
export function useEmailBinding(options: UseEmailBindingOptions = {}): UseEmailBindingResult {
  const { currentEmail, onSuccess, onError } = options;
  const api = useMemo<EmailBindingApi>(
    () => ({ ...defaultApi, ...(options.api || {}) }),
    [options.api],
  );

  const [mode, setMode] = useState<EmailBindingMode>('bind');
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [newCodeSending, setNewCodeSending] = useState(false);
  const [oldCodeSending, setOldCodeSending] = useState(false);

  const newCountdown = useCountdown();
  const oldCountdown = useCountdown();

  const openModal = useCallback(
    (next: EmailBindingMode) => {
      setMode(next);
      setOpen(true);
      newCountdown.reset();
      oldCountdown.reset();
    },
    [newCountdown, oldCountdown],
  );

  const closeModal = useCallback(() => {
    setOpen(false);
    newCountdown.reset();
    oldCountdown.reset();
  }, [newCountdown, oldCountdown]);

  const sendNewCode = useCallback(
    async (email: string): Promise<boolean> => {
      const normalized = normalizeEmail(email);
      if (!normalized) {
        onError?.(new Error('请先输入邮箱'), 'send-code');
        return false;
      }
      if (!isValidEmail(normalized)) {
        onError?.(new Error('邮箱格式不正确'), 'send-code');
        return false;
      }
      if (currentEmail && normalizeEmail(currentEmail) === normalized && mode === 'change') {
        onError?.(new Error('新邮箱不能与当前邮箱相同'), 'send-code');
        return false;
      }
      setNewCodeSending(true);
      try {
        await api.sendCode(normalized);
        newCountdown.start(60);
        return true;
      } catch (error) {
        onError?.(error, 'send-code');
        return false;
      } finally {
        setNewCodeSending(false);
      }
    },
    [api, currentEmail, mode, newCountdown, onError],
  );

  const sendOldCode = useCallback(async (): Promise<boolean> => {
    if (!currentEmail) {
      onError?.(new Error('当前未绑定邮箱'), 'send-code');
      return false;
    }
    setOldCodeSending(true);
    try {
      // 不传 email 时，后端会发送到当前已绑定邮箱
      await api.sendCode();
      oldCountdown.start(60);
      return true;
    } catch (error) {
      onError?.(error, 'send-code');
      return false;
    } finally {
      setOldCodeSending(false);
    }
  }, [api, currentEmail, oldCountdown, onError]);

  const finishSuccess = useCallback(
    async (which: EmailBindingMode) => {
      setOpen(false);
      newCountdown.reset();
      oldCountdown.reset();
      try {
        await onSuccess?.(which);
      } catch {
        /* 静默 */
      }
    },
    [newCountdown, oldCountdown, onSuccess],
  );

  const submitBind = useCallback<UseEmailBindingResult['submitBind']>(
    async ({ email, code }) => {
      const normalized = normalizeEmail(email);
      if (!normalized || !isValidEmail(normalized)) {
        onError?.(new Error('邮箱格式不正确'), 'submit');
        return false;
      }
      if (!code) {
        onError?.(new Error('请输入验证码'), 'submit');
        return false;
      }
      setSubmitting(true);
      try {
        await api.bind({ email: normalized, code });
        await finishSuccess('bind');
        return true;
      } catch (error) {
        onError?.(error, 'submit');
        return false;
      } finally {
        setSubmitting(false);
      }
    },
    [api, finishSuccess, onError],
  );

  const submitUnbind = useCallback<UseEmailBindingResult['submitUnbind']>(
    async ({ code }) => {
      if (!code) {
        onError?.(new Error('请输入验证码'), 'submit');
        return false;
      }
      setSubmitting(true);
      try {
        await api.unbind({ code });
        await finishSuccess('unbind');
        return true;
      } catch (error) {
        onError?.(error, 'submit');
        return false;
      } finally {
        setSubmitting(false);
      }
    },
    [api, finishSuccess, onError],
  );

  const submitChange = useCallback<UseEmailBindingResult['submitChange']>(
    async ({ newEmail, newEmailCode, oldEmailCode }) => {
      const normalized = normalizeEmail(newEmail);
      if (!normalized || !isValidEmail(normalized)) {
        onError?.(new Error('邮箱格式不正确'), 'submit');
        return false;
      }
      if (currentEmail && normalizeEmail(currentEmail) === normalized) {
        onError?.(new Error('新邮箱不能与当前邮箱相同'), 'submit');
        return false;
      }
      if (!newEmailCode || !oldEmailCode) {
        onError?.(new Error('请填写完整验证码'), 'submit');
        return false;
      }
      setSubmitting(true);
      try {
        await api.change({
          newEmail: normalized,
          newEmailCode,
          oldEmailCode,
        });
        await finishSuccess('change');
        return true;
      } catch (error) {
        onError?.(error, 'submit');
        return false;
      } finally {
        setSubmitting(false);
      }
    },
    [api, currentEmail, finishSuccess, onError],
  );

  return {
    mode,
    open,
    submitting,
    newCodeCountdown: newCountdown.count,
    oldCodeCountdown: oldCountdown.count,
    newCodeSending,
    oldCodeSending,
    openModal,
    closeModal,
    sendNewCode,
    sendOldCode,
    submitBind,
    submitUnbind,
    submitChange,
  };
}
