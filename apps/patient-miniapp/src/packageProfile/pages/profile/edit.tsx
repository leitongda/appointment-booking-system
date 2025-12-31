import { View, Text, Image, Input as TaroInput, Picker, Button as TaroButton } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { userApi } from '@hospital/api';
import { STORAGE_KEYS } from '@hospital/shared';
import { getToken, setStorage } from '../../../utils/auth';
import { getFontMode, type FontMode } from '../../../utils/fontMode';
import { UserIcon } from '../../../components/Icons';
import LoginPopup from '../../../components/LoginPopup';
import type { User } from '@hospital/shared';
import './edit.less';

// 性别选项
const GENDER_OPTIONS = ['保密', '男', '女'];

// API 基础 URL
const API_BASE_URL = process.env.TARO_APP_API_URL || 'http://localhost:8000/api/v1';

const ProfileEditPage = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [showLoginPopup, setShowLoginPopup] = useState(false);

  // 表单数据
  const [nickname, setNickname] = useState('');
  const [avatar, setAvatar] = useState('');
  const [gender, setGender] = useState(0);

  // 字体模式
  const [fontMode] = useState<FontMode>(getFontMode());

  useEffect(() => {
    checkLoginAndLoad();
  }, []);

  const checkLoginAndLoad = async () => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      setShowLoginPopup(true);
      return;
    }
    await loadProfile();
  };

  const loadProfile = async () => {
    setLoading(true);
    try {
      const data = await userApi.getProfile();
      setUser(data);
      setNickname(data.nickname || '');
      setAvatar(data.avatar || '');
      setGender(data.gender || 0);
    } catch (error) {
      console.error('加载用户信息失败', error);
      Taro.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
    loadProfile();
  };

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

      if (uploadResult.statusCode === 200) {
        const data = JSON.parse(uploadResult.data);
        if (data.url) {
          setAvatar(data.url);
          Taro.showToast({ title: '头像上传成功', icon: 'success' });
        } else {
          throw new Error('上传响应格式错误');
        }
      } else {
        const errorData = JSON.parse(uploadResult.data);
        throw new Error(errorData.detail || '上传失败');
      }
    } catch (error: any) {
      console.error('头像上传失败', error);
      Taro.showToast({ title: error.message || '头像上传失败', icon: 'none' });
    } finally {
      setUploading(false);
    }
  };

  // 昵称输入
  const handleNicknameInput = (e: any) => {
    setNickname(e.detail.value);
  };

  // 昵称获取（微信昵称）
  const handleNicknameBlur = (e: any) => {
    const value = e.detail.value;
    if (value) {
      setNickname(value);
    }
  };

  // 性别选择
  const handleGenderChange = (e: any) => {
    const index = parseInt(e.detail.value, 10);
    setGender(index);
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

      // 如果有新头像
      if (avatar && avatar !== user?.avatar) {
        updateData.avatar = avatar;
      }

      const updatedUser = await userApi.updateProfile(updateData);
      
      // 更新本地存储
      setStorage(STORAGE_KEYS.USER_INFO, updatedUser);
      
      Taro.showToast({ title: '保存成功', icon: 'success' });
      
      // 延迟返回，让用户看到成功提示
      setTimeout(() => {
        Taro.navigateBack();
      }, 1000);
    } catch (error: any) {
      console.error('保存失败', error);
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
              <Image src={avatar} className="avatar-image" mode="aspectFill" />
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
          {/* 获取微信头像按钮 */}
          <TaroButton
            openType="chooseAvatar"
            onChooseAvatar={handleChooseWechatAvatar}
            className="action-btn wechat-btn"
          >
            微信头像
          </TaroButton>

          {/* 从相册选择按钮 */}
          <TaroButton
            className="action-btn album-btn"
            onClick={handleChooseAlbum}
          >
            从相册选择
          </TaroButton>
        </View>
      </View>

      {/* 表单区域 */}
      <View className="form-section">
        {/* 昵称 */}
        <View className="form-item">
          <Text className="form-label">昵称</Text>
          <TaroInput
            type="nickname"
            className="form-input"
            placeholder="请输入昵称"
            value={nickname}
            onInput={handleNicknameInput}
            onBlur={handleNicknameBlur}
          />
        </View>

        {/* 性别 */}
        <View className="form-item">
          <Text className="form-label">性别</Text>
          <Picker mode="selector" range={GENDER_OPTIONS} value={gender} onChange={handleGenderChange}>
            <View className="gender-picker">
              <Text className={`gender-value ${gender === 0 ? 'placeholder' : ''}`}>
                {GENDER_OPTIONS[gender]}
              </Text>
              <Text className="picker-arrow">›</Text>
            </View>
          </Picker>
        </View>

        {/* 手机号（只读） */}
        <View className="form-item">
          <Text className="form-label">手机号</Text>
          <Text className="form-value">
            {user?.phone ? user.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') : '未绑定'}
          </Text>
        </View>
      </View>

      {/* 底部保存按钮 */}
      <View className="submit-section">
        <Button
          type="primary"
          className="submit-btn"
          loading={saving}
          disabled={saving || uploading}
          onClick={handleSave}
        >
          {saving ? '保存中...' : '保存'}
        </Button>
      </View>

      {/* 上传中遮罩 */}
      {uploading && (
        <View className="loading-overlay">
          <Text className="loading-text">上传中...</Text>
        </View>
      )}

      {/* 加载中遮罩 */}
      {loading && (
        <View className="loading-overlay">
          <Text className="loading-text">加载中...</Text>
        </View>
      )}

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={() => {
          setShowLoginPopup(false);
          if (!getToken()) {
            Taro.navigateBack();
          }
        }}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default ProfileEditPage;

