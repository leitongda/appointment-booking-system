import { Dialog, Input, Toast } from 'antd-mobile';
import { useEffect, useState } from 'react';
import type { UseEmailBindingResult } from '@hospital/api';
import { Button } from '@/components/ui';

interface EmailBindingDialogProps {
  binding: UseEmailBindingResult;
  /** 当前已绑定邮箱（用于解绑/换绑场景展示） */
  currentEmail?: string | null;
}

/** 把完整邮箱遮罩成 `a***b@example.com` 形式 */
function maskEmail(email?: string | null): string {
  if (!email) return '';
  const at = email.indexOf('@');
  if (at <= 0) return email;
  const user = email.slice(0, at);
  const domain = email.slice(at);
  if (user.length <= 1) return `*${domain}`;
  if (user.length === 2) return `${user[0]}*${domain}`;
  const middleStars = '*'.repeat(Math.min(user.length - 2, 4));
  return `${user[0]}${middleStars}${user[user.length - 1]}${domain}`;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const EmailBindingDialog: React.FC<EmailBindingDialogProps> = ({ binding, currentEmail }) => {
  const {
    mode,
    open,
    submitting,
    newCodeCountdown,
    oldCodeCountdown,
    newCodeSending,
    oldCodeSending,
    closeModal,
    sendNewCode,
    sendOldCode,
    submitBind,
    submitUnbind,
    submitChange,
  } = binding;

  const [emailValue, setEmailValue] = useState('');
  const [emailCode, setEmailCode] = useState('');
  const [oldEmailCodeValue, setOldEmailCodeValue] = useState('');

  // 弹窗关闭时清空字段
  useEffect(() => {
    if (!open) {
      setEmailValue('');
      setEmailCode('');
      setOldEmailCodeValue('');
    }
  }, [open]);

  const title = mode === 'bind' ? '绑定邮箱' : mode === 'unbind' ? '解绑邮箱' : '更换邮箱';

  const handleEmailBlur = () => {
    setEmailValue((v) => v.trim().toLowerCase());
  };

  const handleSendNewCode = async () => {
    await sendNewCode(emailValue);
  };

  const newCountdownLabel =
    newCodeSending
      ? '发送中'
      : newCodeCountdown > 0
        ? `重新发送(${newCodeCountdown}s)`
        : '获取验证码';
  const oldCountdownLabel =
    oldCodeSending
      ? '发送中'
      : oldCodeCountdown > 0
        ? `重新发送(${oldCodeCountdown}s)`
        : '获取验证码';

  const handleConfirm = async () => {
    if (mode === 'bind') {
      if (!emailValue || !EMAIL_REGEX.test(emailValue)) {
        Toast.show({ content: '邮箱格式不正确', icon: 'fail' });
        return;
      }
      if (!emailCode) {
        Toast.show({ content: '请输入验证码', icon: 'fail' });
        return;
      }
      await submitBind({ email: emailValue, code: emailCode });
    } else if (mode === 'unbind') {
      if (!emailCode) {
        Toast.show({ content: '请输入验证码', icon: 'fail' });
        return;
      }
      await submitUnbind({ code: emailCode });
    } else {
      if (!emailValue || !EMAIL_REGEX.test(emailValue)) {
        Toast.show({ content: '新邮箱格式不正确', icon: 'fail' });
        return;
      }
      if (!emailCode || !oldEmailCodeValue) {
        Toast.show({ content: '请填写完整验证码', icon: 'fail' });
        return;
      }
      await submitChange({
        newEmail: emailValue,
        newEmailCode: emailCode,
        oldEmailCode: oldEmailCodeValue,
      });
    }
  };

  const renderContent = () => {
    if (mode === 'bind') {
      return (
        <>
          <div style={{ marginBottom: 12 }}>
            <div style={{ marginBottom: 4, fontSize: 14, color: '#666' }}>邮箱地址</div>
            <Input
              placeholder="请输入邮箱地址"
              value={emailValue}
              onChange={setEmailValue}
              onBlur={handleEmailBlur}
              clearable
              type="email"
              aria-label="邮箱地址"
            />
          </div>
          <div style={{ marginBottom: 12 }}>
            <div style={{ marginBottom: 4, fontSize: 14, color: '#666' }}>验证码</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <Input
                placeholder="请输入验证码"
                value={emailCode}
                onChange={setEmailCode}
                maxLength={6}
                clearable
                type="tel"
                style={{ flex: 1 }}
                aria-label="邮箱验证码"
              />
              <Button
                size="sm"
                disabled={newCodeCountdown > 0 || newCodeSending}
                onClick={handleSendNewCode}
                style={{ whiteSpace: 'nowrap' }}
                aria-label={
                  newCodeCountdown > 0
                    ? `${newCodeCountdown}秒后可重新发送`
                    : '获取验证码'
                }
              >
                {newCountdownLabel}
              </Button>
            </div>
          </div>
        </>
      );
    }
    if (mode === 'unbind') {
      return (
        <>
          <div style={{ marginBottom: 12, fontSize: 14, color: '#666' }}>
            验证码将发送到当前绑定的邮箱：<strong>{maskEmail(currentEmail)}</strong>
          </div>
          <div style={{ marginBottom: 12 }}>
            <div style={{ marginBottom: 4, fontSize: 14, color: '#666' }}>验证码</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <Input
                placeholder="请输入验证码"
                value={emailCode}
                onChange={setEmailCode}
                maxLength={6}
                clearable
                type="tel"
                style={{ flex: 1 }}
                aria-label="邮箱验证码"
              />
              <Button
                size="sm"
                disabled={oldCodeCountdown > 0 || oldCodeSending}
                onClick={() => sendOldCode()}
                style={{ whiteSpace: 'nowrap' }}
                aria-label={
                  oldCodeCountdown > 0
                    ? `${oldCodeCountdown}秒后可重新发送`
                    : '获取验证码'
                }
              >
                {oldCountdownLabel}
              </Button>
            </div>
          </div>
        </>
      );
    }
    // change
    return (
      <>
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4, fontSize: 14, color: '#666' }}>新邮箱地址</div>
          <Input
            placeholder="请输入新邮箱地址"
            value={emailValue}
            onChange={setEmailValue}
            onBlur={handleEmailBlur}
            clearable
            type="email"
            aria-label="新邮箱地址"
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4, fontSize: 14, color: '#666' }}>新邮箱验证码</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <Input
              placeholder="请输入新邮箱验证码"
              value={emailCode}
              onChange={setEmailCode}
              maxLength={6}
              clearable
              type="tel"
              style={{ flex: 1 }}
              aria-label="新邮箱验证码"
            />
            <Button
              size="sm"
              disabled={newCodeCountdown > 0 || newCodeSending}
              onClick={handleSendNewCode}
              style={{ whiteSpace: 'nowrap' }}
            >
              {newCountdownLabel}
            </Button>
          </div>
        </div>
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4, fontSize: 14, color: '#666' }}>
            旧邮箱验证码（{maskEmail(currentEmail) || '当前邮箱'}）
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <Input
              placeholder="请输入旧邮箱验证码"
              value={oldEmailCodeValue}
              onChange={setOldEmailCodeValue}
              maxLength={6}
              clearable
              type="tel"
              style={{ flex: 1 }}
              aria-label="旧邮箱验证码"
            />
            <Button
              size="sm"
              disabled={oldCodeCountdown > 0 || oldCodeSending}
              onClick={() => sendOldCode()}
              style={{ whiteSpace: 'nowrap' }}
            >
              {oldCountdownLabel}
            </Button>
          </div>
        </div>
      </>
    );
  };

  return (
    <Dialog
      visible={open}
      title={title}
      content={<div style={{ padding: '8px 0' }}>{renderContent()}</div>}
      // 不使用 closeOnAction —— 校验不通过时不能强制关闭
      actions={[
        [
          {
            key: 'cancel',
            text: '取消',
            onClick: () => closeModal(),
          },
          {
            key: 'confirm',
            text: submitting ? '提交中...' : '确认',
            bold: true,
            disabled: submitting,
            onClick: async (e?: React.MouseEvent) => {
              // 阻止 Dialog 默认的关闭行为，由 hook 在成功时主动关闭
              e?.preventDefault?.();
              await handleConfirm();
            },
          },
        ],
      ]}
      onClose={closeModal}
    />
  );
};

export default EmailBindingDialog;
export { maskEmail };
