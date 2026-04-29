import { NavBar, Switch, Picker, Toast, Dialog } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { notificationPreferenceApi } from '@hospital/api';
import type { NotificationPreference } from '@hospital/api';
import { Card } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

const HOURS = Array.from({ length: 24 }, (_, i) => ({
  label: `${String(i).padStart(2, '0')}:00`,
  value: `${String(i).padStart(2, '0')}:00`,
}));

const MINUTES = Array.from({ length: 60 }, (_, i) => ({
  label: `:${String(i).padStart(2, '0')}`,
  value: String(i).padStart(2, '0'),
}));

const TIME_COLUMNS = [HOURS, MINUTES];

const formatTime = (timeStr: string | undefined): string => {
  if (!timeStr) return '未设置';
  return timeStr;
};

const parseTimeValue = (timeStr: string | undefined): [string, string] | null => {
  if (!timeStr) return null;
  const [hour, minute] = timeStr.split(':');
  return [hour, minute];
};

const NotificationSettingsPage: React.FC = () => {
  const [preference, setPreference] = useState<NotificationPreference>({
    id: '',
    appointmentEnabled: true,
    reminderEnabled: true,
    queueCallEnabled: true,
    stopClinicEnabled: true,
    systemEnabled: true,
    smsEnabled: true,
    emailEnabled: false,
    wechatEnabled: true,
    inAppEnabled: true,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [startTimeVisible, setStartTimeVisible] = useState(false);
  const [endTimeVisible, setEndTimeVisible] = useState(false);
  const [quietHoursEnabled, setQuietHoursEnabled] = useState(false);

  useEffect(() => {
    loadPreferences();
  }, []);

  useEffect(() => {
    const hasQuietHours = preference.quietHoursStart || preference.quietHoursEnd;
    setQuietHoursEnabled(!!hasQuietHours);
  }, [preference]);

  const loadPreferences = async () => {
    try {
      setLoading(true);
      const data = await notificationPreferenceApi.get();
      setPreference(data);
    } catch (error) {
      console.error('加载通知偏好失败', error);
      Toast.show({ content: '加载失败，请重试', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  const updatePreference = useCallback(
    async (updates: Partial<NotificationPreference>) => {
      try {
        setSaving(true);
        const updated = await notificationPreferenceApi.update(updates);
        setPreference(updated);
        return true;
      } catch (error) {
        console.error('保存通知偏好失败', error);
        Toast.show({ content: '保存失败，请重试', icon: 'fail' });
        return false;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const handleToggle = async (
    key: keyof NotificationPreference,
    value: boolean
  ) => {
    const success = await updatePreference({ [key]: value });
    if (!success) {
      setPreference(prev => ({ ...prev, [key]: !value }));
    }
  };

  const handleTimePickerConfirm = async (
    type: 'start' | 'end',
    value: string[]
  ) => {
    const timeStr = `${value[0]}:${value[1]}`;
    const updates: Partial<NotificationPreference> =
      type === 'start'
        ? { quietHoursStart: timeStr }
        : { quietHoursEnd: timeStr };

    await updatePreference(updates);
  };

  const handleToggleQuietHours = async (enabled: boolean) => {
    if (!enabled) {
      const result = await Dialog.confirm({
        content: '关闭免打扰时段后，将全天接收通知，确定关闭吗？',
      });
      if (!result) return;

      await updatePreference({
        quietHoursStart: undefined,
        quietHoursEnd: undefined,
      });
    } else {
      await updatePreference({
        quietHoursStart: '22:00',
        quietHoursEnd: '08:00',
      });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-muted-foreground">加载中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <NavBar
        onBack={() => history.back()}
        className="!bg-card border-b border-border"
      >
        通知设置
      </NavBar>

      <motion.div
        className="p-4 space-y-4"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {/* Notification Types */}
        <motion.div variants={fadeInUp}>
          <div className="mb-2 px-1">
            <span className="text-xs text-muted-foreground uppercase tracking-wider font-mono">
              通知类型
            </span>
          </div>
          <Card variant="default" padding="none" animated={false}>
            <SwitchItem
              icon={<BellIcon />}
              label="预约通知"
              checked={preference.appointmentEnabled}
              onChange={(v) => handleToggle('appointmentEnabled', v)}
              disabled={saving}
            />
            <div className="border-t border-border" />
            <SwitchItem
              icon={<ClockIcon />}
              label="提醒通知"
              checked={preference.reminderEnabled}
              onChange={(v) => handleToggle('reminderEnabled', v)}
              disabled={saving}
            />
            <div className="border-t border-border" />
            <SwitchItem
              icon={<SpeakerIcon />}
              label="叫号通知"
              checked={preference.queueCallEnabled}
              onChange={(v) => handleToggle('queueCallEnabled', v)}
              disabled={saving}
            />
            <div className="border-t border-border" />
            <SwitchItem
              icon={<AlertIcon />}
              label="停诊通知"
              checked={preference.stopClinicEnabled}
              onChange={(v) => handleToggle('stopClinicEnabled', v)}
              disabled={saving}
            />
            <div className="border-t border-border" />
            <SwitchItem
              icon={<SystemIcon />}
              label="系统通知"
              checked={preference.systemEnabled}
              onChange={(v) => handleToggle('systemEnabled', v)}
              disabled={saving}
            />
          </Card>
        </motion.div>

        {/* Notification Channels */}
        <motion.div variants={fadeInUp}>
          <div className="mb-2 px-1">
            <span className="text-xs text-muted-foreground uppercase tracking-wider font-mono">
              通知渠道
            </span>
          </div>
          <Card variant="default" padding="none" animated={false}>
            <SwitchItem
              icon={<SmsIcon />}
              label="短信通知"
              checked={preference.smsEnabled}
              onChange={(v) => handleToggle('smsEnabled', v)}
              disabled={saving}
            />
            <div className="border-t border-border" />
            <SwitchItem
              icon={<WechatIcon />}
              label="微信通知"
              checked={preference.wechatEnabled}
              onChange={(v) => handleToggle('wechatEnabled', v)}
              disabled={saving}
            />
            <div className="border-t border-border" />
            <SwitchItem
              icon={<AppIcon />}
              label="站内信"
              checked={preference.inAppEnabled}
              onChange={(v) => handleToggle('inAppEnabled', v)}
              disabled={saving}
            />
          </Card>
        </motion.div>

        {/* Quiet Hours */}
        <motion.div variants={fadeInUp}>
          <div className="mb-2 px-1">
            <span className="text-xs text-muted-foreground uppercase tracking-wider font-mono">
              免打扰时段
            </span>
          </div>
          <Card variant="default" padding="none" animated={false}>
            <div className="flex items-center justify-between px-4 py-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-accent">
                  <MoonIcon />
                </div>
                <div className="flex flex-col">
                  <span className="font-medium text-foreground">启用免打扰</span>
                  <span className="text-xs text-muted-foreground">
                    开启后将不会收到通知
                  </span>
                </div>
              </div>
              <Switch
                checked={quietHoursEnabled}
                onChange={handleToggleQuietHours}
                disabled={saving}
                style={{
                  '--checked-color': '#0052FF',
                } as React.CSSProperties}
              />
            </div>

            {quietHoursEnabled && (
              <>
                <div className="border-t border-border" />
                <div
                  className="flex items-center justify-between px-4 py-4 active:bg-muted transition-colors"
                  onClick={() => setStartTimeVisible(true)}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-accent">
                      <span className="text-sm font-medium">始</span>
                    </div>
                    <span className="font-medium text-foreground">开始时间</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground font-mono">
                      {formatTime(preference.quietHoursStart)}
                    </span>
                    <svg
                      className="w-4 h-4 text-muted-foreground"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </div>
                </div>

                <div className="border-t border-border" />
                <div
                  className="flex items-center justify-between px-4 py-4 active:bg-muted transition-colors"
                  onClick={() => setEndTimeVisible(true)}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-accent">
                      <span className="text-sm font-medium">终</span>
                    </div>
                    <span className="font-medium text-foreground">结束时间</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground font-mono">
                      {formatTime(preference.quietHoursEnd)}
                    </span>
                    <svg
                      className="w-4 h-4 text-muted-foreground"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </div>
                </div>
              </>
            )}
          </Card>
        </motion.div>
      </motion.div>

      <Picker
        columns={TIME_COLUMNS}
        visible={startTimeVisible}
        onClose={() => setStartTimeVisible(false)}
        value={parseTimeValue(preference.quietHoursStart) || undefined}
        onConfirm={(value) =>
          handleTimePickerConfirm('start', value as string[])
        }
      />

      <Picker
        columns={TIME_COLUMNS}
        visible={endTimeVisible}
        onClose={() => setEndTimeVisible(false)}
        value={parseTimeValue(preference.quietHoursEnd) || undefined}
        onConfirm={(value) =>
          handleTimePickerConfirm('end', value as string[])
        }
      />
    </div>
  );
};

interface SwitchItemProps {
  icon: React.ReactNode;
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
}

const SwitchItem: React.FC<SwitchItemProps> = ({
  icon,
  label,
  checked,
  onChange,
  disabled,
}) => (
  <div className="flex items-center justify-between px-4 py-4">
    <div className="flex items-center gap-3">
      <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-accent">
        {icon}
      </div>
      <span className="font-medium text-foreground">{label}</span>
    </div>
    <Switch
      checked={checked}
      onChange={onChange}
      disabled={disabled}
      style={{
        '--checked-color': '#0052FF',
      } as React.CSSProperties}
    />
  </div>
);

const BellIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
    />
  </svg>
);

const ClockIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
    />
  </svg>
);

const SpeakerIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"
    />
  </svg>
);

const AlertIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
    />
  </svg>
);

const SystemIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
    />
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
    />
  </svg>
);

const ChatBubbleIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
    />
  </svg>
);

const SmsIcon = ChatBubbleIcon;
const AppIcon = ChatBubbleIcon;

const WechatIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
    />
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M17 9c.823 0 1.613.158 2.32.447M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728"
    />
  </svg>
);

const MoonIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
    />
  </svg>
);

export default NotificationSettingsPage;
