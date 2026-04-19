import { View, Text, Image, Input as TaroInput, Picker, Button as TaroButton } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useCallback } from 'react';
import { userApi } from '@hospital/api';
import { STORAGE_KEYS } from '@hospital/shared';
import { getToken, setStorage } from '../../../../utils/auth';
import { useProtectedPage } from '../../../../hooks/useProtectedPage';
import { getFontMode, type FontMode } from '../../../../utils/fontMode';
import { useApplyThemeNavigationBar } from '../../../../utils/theme';
import { UserIcon } from '../../../../components/Icons';
import LoginPopup from '../../../../components/LoginPopup';
import { getImageUrl } from '../../../../utils/url';
import type { User } from '@hospital/shared';
import './index.less';

// 性别选项
const GENDER_OPTIONS = ['保密', '男', '女'];

// API 基础 URL
const API_BASE_URL = process.env.TARO_APP_API_URL || 'http://localhost:8000/api/v1';

const ProfileEditPage = () => {
  useApplyThemeNavigationBar();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  // 表单数据
  const [nickname, setNickname] = useState('');
  const [avatar, setAvatar] = useState('');
  const [gender, setGender] = useState(0);

  // 手机号编辑
  const [isEditingPhone, setIsEditingPhone] = useState(false);
  const [newPhone, setNewPhone] = useState('');
  const [phoneBinding, setPhoneBinding] = useState(false);

  // 字体模式
  const [fontMode] = useState<FontMode>(getFontMode());

  const loadProfile = useCallback(async () => {
    setLoading(true);
    try {
      const data = await userApi.getProfile();
      setUser(data);
      setNickname(data.nickname || '');
      setAvatar(data.avatar || '');
      setGender(data.gender ?? 0);
    } catch (error) {
      console.error('加载用户信息失败', error);
      Taro.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  }, []);

  const { showLoginPopup, handleLoginSuccess, handleLoginClose } = useProtectedPage({
    load: loadProfile,
    clear: () => {
      setUser(null);
      setLoading(false);
    },
  });

  // 获取微信头像
  const handleChooseWechatAvatar = (e: any) => {
    const avatarUrl = e.detail.avatarUrl;
    if (avatarUrl) {
      uploadAvatar(avatarUrl);
    }
  };

  // 从相册选择头像
  const handleChooseAlbum = async () => {
    try {
      const res = await Taro.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album'],
      });

      if (res.tempFilePaths && res.tempFilePaths.length > 0) {
        uploadAvatar(res.tempFilePaths[0]);
      }
    } catch (error) {
      console.log('用户取消选择图片');
    }
  };

  // 上传头像到服务器
  const uploadAvatar = async (filePath: string) => {
    const token = getToken();
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    setUploading(true);
    try {
      const uploadResult = await Taro.uploadFile({
        url: `${API_BASE_URL}/users/avatar`,
        filePath: filePath,
        name: 'file',
        header: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (uploadResult.statusCode >= 200 && uploadResult.statusCode < 300) {
        let response: any;
        try {
          response = JSON.parse(uploadResult.data);
        } catch (parseError) {
          throw new Error('服务器响应格式错误');
        }

        const avatarUrl = response.data?.url || response.url;
        if (avatarUrl) {
          setAvatar(avatarUrl);
          Taro.showToast({ title: '头像上传成功', icon: 'success' });
        } else {
          throw new Error('上传成功但未获取到头像地址');
        }
      } else {
        let errorMessage = '上传失败';
        try {
          const errorResponse = JSON.parse(uploadResult.data);
          errorMessage = errorResponse.message || errorResponse.detail || '上传失败';
        } catch {
          errorMessage = `上传失败(${uploadResult.statusCode})`;
        }
        throw new Error(errorMessage);
      }
    } catch (error: any) {
      Taro.showToast({ title: error.message || '头像上传失败', icon: 'none' });
    } finally {
      setUploading(false);
    }
  };

  // 昵称输入
  const handleNicknameInput = (e: any) => {
    setNickname(e.detail.value);
  };

  // 昵称失焦
  const handleNicknameBlur = (e: any) => {
    const value = e.detail.value;
    if (value && value !== nickname) {
      setNickname(value);
    }
  };

  // 昵称审核完成回调
  const handleNickNameReview = (e: any) => {
    console.log('昵称审核结果:', e.detail);
  };

  // 性别选择
  const handleGenderChange = (e: any) => {
    setGender(parseInt(e.detail.value, 10));
  };

  // 手机号编辑
  const handlePhoneClick = () => {
    setNewPhone(user?.phone || '');
    setIsEditingPhone(true);
  };

  const handlePhoneInput = (e: any) => {
    setNewPhone(e.detail.value.replace(/\D/g, '').slice(0, 11));
  };

  const handlePhoneCancel = (e: any) => {
    e.stopPropagation();
    setIsEditingPhone(false);
    setNewPhone('');
  };

  const handlePhoneSave = async (e: any) => {
    e.stopPropagation();
    if (!/^1\d{10}$/.test(newPhone)) {
      Taro.showToast({ title: '请输入正确的手机号', icon: 'none' });
      return;
    }
    if (newPhone === user?.phone) {
      setIsEditingPhone(false);
      return;
    }

    setPhoneBinding(true);
    try {
      await userApi.bindPhone({ phone: newPhone });
      if (user) {
        const updatedUser = { ...user, phone: newPhone };
        setUser(updatedUser);
        setStorage(STORAGE_KEYS.USER_INFO, updatedUser);
      }
      Taro.showToast({ title: '手机号绑定成功', icon: 'success' });
      setIsEditingPhone(false);
    } catch (error: any) {
      Taro.showToast({ title: error.message || '绑定失败', icon: 'none' });
    } finally {
      setPhoneBinding(false);
    }
  };

  // 保存资料
  const handleSave = async () => {
    if (!nickname.trim()) {
      Taro.showToast({ title: '请输入昵称', icon: 'none' });
      return;
    }

    setSaving(true);
    try {
      const updateData: Partial<User> = {
        nickname: nickname.trim(),
        gender: gender,
      };

      if (avatar && avatar !== user?.avatar) {
        updateData.avatar = avatar;
      }

      const updatedUser = await userApi.updateProfile(updateData);
      setStorage(STORAGE_KEYS.USER_INFO, updatedUser);
      Taro.showToast({ title: '保存成功', icon: 'success' });
      setTimeout(() => Taro.navigateBack(), 1000);
    } catch (error: any) {
      Taro.showToast({ title: error.message || '保存失败', icon: 'none' });
    } finally {
      setSaving(false);
    }
  };

  const fontModeClass = fontMode === 'elder' ? 'font-mode-elder' : '';

  return (
    <View className={`profile-edit-page ${fontModeClass}`}>
      {/* 头像区域 */}
      <View className="avatar-section">
        <View className="avatar-wrapper">
          <View className="avatar-container">
            {avatar ? (
              <Image src={getImageUrl(avatar)} className="avatar-image" mode="aspectFill" />
            ) : (
              <View className="avatar-placeholder">
                <UserIcon size={60} color="#94A3B8" />
              </View>
            )}
          </View>
          <View className="avatar-edit-badge">
            <Text className="edit-icon">✎</Text>
          </View>
        </View>
        <View className="avatar-actions">
          <TaroButton openType="chooseAvatar" onChooseAvatar={handleChooseWechatAvatar} className="action-btn wechat-btn">
            微信头像
          </TaroButton>
          <TaroButton className="action-btn album-btn" onClick={handleChooseAlbum}>
            从相册选择
          </TaroButton>
        </View>
      </View>

      {/* 表单区域 */}
      <View className="form-section">
        <View className="form-item">
          <Text className="form-label">昵称</Text>
          <View className="form-input-wrapper">
            <TaroInput type="nickname" className="form-input" placeholder="点击输入或使用微信昵称" value={nickname} onInput={handleNicknameInput} onBlur={handleNicknameBlur}
              // @ts-ignore
              onNickNameReview={handleNickNameReview}
            />
          </View>
        </View>
        <Text className="form-hint">真机上点击输入框，键盘上方会显示"使用微信昵称"选项</Text>

        <View className="form-item">
          <Text className="form-label">性别</Text>
          <Picker mode="selector" range={GENDER_OPTIONS} value={gender} onChange={handleGenderChange}>
            <View className="gender-picker">
              <Text className={`gender-value ${gender === 0 ? 'placeholder' : ''}`}>{GENDER_OPTIONS[gender]}</Text>
              <Text className="picker-arrow">›</Text>
            </View>
          </Picker>
        </View>

        <View className="form-item" onClick={!isEditingPhone ? handlePhoneClick : undefined}>
          <Text className="form-label">手机号</Text>
          {isEditingPhone ? (
            <View className="phone-edit-wrapper">
              <TaroInput type="number" className="form-input phone-input" placeholder="请输入手机号" value={newPhone} onInput={handlePhoneInput} maxlength={11} focus />
              <View className="phone-actions">
                <Text className="phone-action-btn cancel" onClick={(e) => handlePhoneCancel(e)}>取消</Text>
                <Text className={`phone-action-btn confirm ${phoneBinding ? 'disabled' : ''}`} onClick={(e) => !phoneBinding && handlePhoneSave(e)}>
                  {phoneBinding ? '保存中' : '确定'}
                </Text>
              </View>
            </View>
          ) : (
            <View className="form-value-wrapper">
              <Text className="form-value">{user?.phone ? user.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') : '未绑定'}</Text>
              <Text className="picker-arrow">›</Text>
            </View>
          )}
        </View>
      </View>

      <View className="submit-section">
        <Button type="primary" className="submit-btn" loading={saving} disabled={saving || uploading} onClick={handleSave}>
          {saving ? '保存中...' : '保存'}
        </Button>
      </View>

      {uploading && <View className="loading-overlay"><Text className="loading-text">上传中...</Text></View>}
      {loading && <View className="loading-overlay"><Text className="loading-text">加载中...</Text></View>}

      <LoginPopup visible={showLoginPopup} onClose={handleLoginClose} onSuccess={handleLoginSuccess} />
    </View>
  );
};

export default ProfileEditPage;
