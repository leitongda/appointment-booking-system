import { View, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Switch, Button, Cell, Dialog, Input } from '@nutui/nutui-react-taro';
import { useState, useEffect, useCallback } from 'react';
import { STORAGE_KEYS } from '@hospital/shared';
import { clearAuthSession, getToken } from '../../../utils/auth';
import { userApi } from '@hospital/api';
import { useProtectedPage } from '../../../hooks/useProtectedPage';
import { getFontMode, applyFontMode, type FontMode } from '../../../utils/fontMode';
import { getCurrentTheme, getCurrentThemeLabel, applyTheme, getThemeList, subscribeThemeChange } from '../../../utils/theme';
import type { ThemeName } from '../../../config/theme.config';
import LoginPopup from '../../../components/LoginPopup';
import './index.less';

const SettingsPage = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [notificationEnabled, setNotificationEnabled] = useState(true);
  const [systemNotificationEnabled, setSystemNotificationEnabled] = useState(true);
  const [userPhone, setUserPhone] = useState('');

  // 字体模式
  const [fontMode, setFontMode] = useState<FontMode>(getFontMode());

  // 主题选择
  const [showThemePicker, setShowThemePicker] = useState(false);
  const [currentTheme, setCurrentTheme] = useState(getCurrentTheme());
  const themeList = getThemeList();

  // 修改密码弹窗
  const [showPasswordDialog, setShowPasswordDialog] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);

  // 绑定手机号弹窗
  const [showPhoneDialog, setShowPhoneDialog] = useState(false);
  const [newPhone, setNewPhone] = useState('');
  const [phoneLoading, setPhoneLoading] = useState(false);

  useEffect(
    () =>
      subscribeThemeChange(({ themeName }) => {
        setCurrentTheme(themeName);
      }),
    []
  );

  const loadUserInfo = useCallback(async () => {
    try {
      const user = await userApi.getProfile();
      setIsLoggedIn(true);
      setUserPhone(user.phone || '');
    } catch (error) {
      console.error('获取用户信息失败', error);
    }
  }, []);

  const { showLoginPopup, handleLoginSuccess, handleLoginClose } = useProtectedPage({
    load: loadUserInfo,
    clear: () => {
      setIsLoggedIn(false);
      setUserPhone('');
    },
  });

  const handleClearCache = async () => {
    const result = await Taro.showModal({
      title: '清除缓存',
      content: '确定要清除本地缓存吗？这不会影响您的账号信息。',
    });

    if (result.confirm) {
      try {
        const token = getToken();
        const storeContext = Taro.getStorageSync(STORAGE_KEYS.STORE_CONTEXT);
        const themeStorageKey = storeContext?.storeId ? `${STORAGE_KEYS.CURRENT_THEME}:${storeContext.storeId}` : '';
        const currentThemeValue = themeStorageKey ? Taro.getStorageSync(themeStorageKey) : '';
        const fontModeValue = Taro.getStorageSync(STORAGE_KEYS.FONT_MODE);
        await Taro.clearStorage();
        if (token) {
          Taro.setStorageSync(STORAGE_KEYS.TOKEN, token);
        }
        if (storeContext) {
          Taro.setStorageSync(STORAGE_KEYS.STORE_CONTEXT, storeContext);
        }
        if (themeStorageKey && currentThemeValue) {
          Taro.setStorageSync(themeStorageKey, currentThemeValue);
        }
        if (fontModeValue) {
          Taro.setStorageSync(STORAGE_KEYS.FONT_MODE, fontModeValue);
        }
        Taro.showToast({ title: '缓存已清除', icon: 'success' });
      } catch (error) {
        Taro.showToast({ title: '清除失败', icon: 'none' });
      }
    }
  };

  const handleChangePassword = () => {
    if (!isLoggedIn) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    setOldPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setShowPasswordDialog(true);
  };

  const handleSubmitPassword = async () => {
    if (!oldPassword) {
      Taro.showToast({ title: '请输入原密码', icon: 'none' });
      return;
    }
    if (!newPassword || newPassword.length < 6) {
      Taro.showToast({ title: '新密码至少6位', icon: 'none' });
      return;
    }
    if (newPassword !== confirmPassword) {
      Taro.showToast({ title: '两次密码不一致', icon: 'none' });
      return;
    }

    setPasswordLoading(true);
    try {
      await userApi.changePassword({
        oldPassword,
        newPassword,
      });
      Taro.showToast({ title: '密码修改成功', icon: 'success' });
      setShowPasswordDialog(false);
    } catch (error: any) {
      Taro.showToast({ title: error.message || '修改失败', icon: 'none' });
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleBindPhone = () => {
    if (!isLoggedIn) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    setNewPhone('');
    setShowPhoneDialog(true);
  };

  const handleSubmitPhone = async () => {
    if (!newPhone || !/^1\d{10}$/.test(newPhone)) {
      Taro.showToast({ title: '请输入正确的手机号', icon: 'none' });
      return;
    }

    setPhoneLoading(true);
    try {
      await userApi.bindPhone({ phone: newPhone });
      Taro.showToast({ title: '手机号绑定成功', icon: 'success' });
      setShowPhoneDialog(false);
      setUserPhone(newPhone);
    } catch (error: any) {
      Taro.showToast({ title: error.message || '绑定失败', icon: 'none' });
    } finally {
      setPhoneLoading(false);
    }
  };

  const handleLogout = async () => {
    const result = await Taro.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
    });

    if (result.confirm) {
      clearAuthSession('logout');
      Taro.showToast({ title: '已退出登录', icon: 'success' });
      // 退出后跳转到首页
      Taro.switchTab({ url: '/pages/index/index' });
    }
  };

  const handleViewAgreement = (type: 'user' | 'privacy') => {
    Taro.navigateTo({ url: `/packageOther/pages/agreement/index?type=${type}` });
  };

  // 切换字体模式
  const handleFontModeChange = (isElder: boolean) => {
    const newMode: FontMode = isElder ? 'elder' : 'standard';
    setFontMode(newMode);
    applyFontMode(newMode);
    Taro.showToast({
      title: isElder ? '已开启长辈模式' : '已切换标准模式',
      icon: 'success'
    });
  };

  // 切换主题
  const handleThemeChange = (themeName: ThemeName) => {
    applyTheme(themeName);
    setCurrentTheme(themeName);
    setShowThemePicker(false);
    Taro.showToast({ title: '主题已切换', icon: 'success' });
  };

  // 根据当前字体模式获取类名
  const fontModeClass = fontMode === 'elder' ? 'font-mode-elder' : '';

  return (
    <View className={`settings-page ${fontModeClass}`}>
      {/* 账号安全 */}
      <View className="section">
        <Text className="section-title">账号安全</Text>
        <View className="cell-group">
          <Cell
            title="修改密码"
            extra={<Text>›</Text>}
            onClick={handleChangePassword}
          />
          <Cell
            title="手机号绑定"
            description={userPhone ? userPhone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') : '未绑定'}
            extra={<Text>›</Text>}
            onClick={handleBindPhone}
          />
        </View>
      </View>

      {/* 通知设置 */}
      <View className="section">
        <Text className="section-title">通知设置</Text>
        <View className="cell-group">
          <Cell
            title="预约提醒"
            extra={
              <Switch
                checked={notificationEnabled}
                onChange={(value) => setNotificationEnabled(value)}
              />
            }
          />
          <Cell
            title="系统通知"
            extra={
              <Switch
                checked={systemNotificationEnabled}
                onChange={(value) => setSystemNotificationEnabled(value)}
              />
            }
          />
        </View>
      </View>

      {/* 显示设置 */}
      <View className="section">
        <Text className="section-title">显示设置</Text>
        <View className="cell-group">
          <Cell
            title="主题风格"
            description={getCurrentThemeLabel()}
            extra={<Text>›</Text>}
            onClick={() => setShowThemePicker(true)}
          />
          <Cell
            title="长辈模式"
            description="开启后字体放大，方便阅读"
            extra={
              <Switch
                checked={fontMode === 'elder'}
                onChange={(value) => handleFontModeChange(value)}
              />
            }
          />
        </View>
      </View>

      {/* 其他设置 */}
      <View className="section">
        <Text className="section-title">其他</Text>
        <View className="cell-group">
          <Cell
            title="清除缓存"
            extra={<Text>›</Text>}
            onClick={handleClearCache}
          />
          <Cell
            title="用户协议"
            extra={<Text>›</Text>}
            onClick={() => handleViewAgreement('user')}
          />
          <Cell
            title="隐私政策"
            extra={<Text>›</Text>}
            onClick={() => handleViewAgreement('privacy')}
          />
        </View>
      </View>

      {/* 退出登录 */}
      {isLoggedIn && (
        <View className="logout-section">
          <Button type="danger" className="logout-btn" block onClick={handleLogout}>
            退出登录
          </Button>
        </View>
      )}

      {/* 修改密码弹窗 */}
      <Dialog
        visible={showPasswordDialog}
        title="修改密码"
        onClose={() => setShowPasswordDialog(false)}
        footer={null}
      >
        <View className="dialog-content">
          <View className="form-item">
            <Text className="form-label">原密码</Text>
            <Input
              type="password"
              placeholder="请输入原密码"
              value={oldPassword}
              onChange={(val) => setOldPassword(val)}
              className="form-input"
            />
          </View>
          <View className="form-item">
            <Text className="form-label">新密码</Text>
            <Input
              type="password"
              placeholder="请输入新密码（至少6位）"
              value={newPassword}
              onChange={(val) => setNewPassword(val)}
              className="form-input"
            />
          </View>
          <View className="form-item">
            <Text className="form-label">确认密码</Text>
            <Input
              type="password"
              placeholder="请再次输入新密码"
              value={confirmPassword}
              onChange={(val) => setConfirmPassword(val)}
              className="form-input"
            />
          </View>
          <Button
            type="primary"
            block
            loading={passwordLoading}
            onClick={handleSubmitPassword}
            className="submit-btn"
          >
            确认修改
          </Button>
        </View>
      </Dialog>

      {/* 绑定手机号弹窗 */}
      <Dialog
        visible={showPhoneDialog}
        title="绑定手机号"
        onClose={() => setShowPhoneDialog(false)}
        footer={null}
      >
        <View className="dialog-content">
          <View className="form-item">
            <Text className="form-label">手机号</Text>
            <Input
              type="tel"
              placeholder="请输入新手机号"
              maxLength={11}
              value={newPhone}
              onChange={(val) => setNewPhone(val)}
              className="form-input"
            />
          </View>
          <Button
            type="primary"
            block
            loading={phoneLoading}
            onClick={handleSubmitPhone}
            className="submit-btn"
          >
            确认绑定
          </Button>
        </View>
      </Dialog>

      {/* 主题选择弹窗 */}
      <Dialog
        visible={showThemePicker}
        title="选择主题"
        onClose={() => setShowThemePicker(false)}
      >
        <View className="theme-picker">
          {themeList.map(theme => (
            <View
              key={theme.value}
              className={`theme-item ${currentTheme === theme.value ? 'active' : ''}`}
              onClick={() => handleThemeChange(theme.value)}
            >
              <View className="theme-color" style={{ background: theme.color }} />
              <Text className="theme-name">{theme.label}</Text>
            </View>
          ))}
        </View>
      </Dialog>

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={handleLoginClose}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default SettingsPage;
