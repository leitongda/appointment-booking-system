import { View, Text, Input as TaroInput, Picker } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Form, Button, Switch } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { userApi } from '@hospital/api';
import { getToken } from '../../../utils/auth';
import LoginPopup from '../../../components/LoginPopup';
import type { Patient } from '@hospital/shared';
import './edit.less';

// 表单数据类型
type PatientFormData = Omit<Patient, 'id' | 'userId'>;

// 性别选项：0-不透露, 1-男, 2-女
const GENDER_OPTIONS = ['不透露', '男', '女'];
const GENDER_VALUE_MAP: Record<number, number> = { 0: 0, 1: 1, 2: 2 };

// 关系选项
const RELATIONSHIP_OPTIONS = ['本人', '父亲', '母亲', '子女', '配偶', '其他'];

const PatientEditPage = () => {
  const router = useRouter();
  const { id } = router.params;
  const isEdit = !!id;

  const [loading, setLoading] = useState(false);
  const [formValues, setFormValues] = useState<Partial<PatientFormData>>({
    gender: 1,
    isDefault: false,
  });
  const [showLoginPopup, setShowLoginPopup] = useState(false);
  
  // 性别和关系选择的索引
  const [genderIndex, setGenderIndex] = useState(1); // 默认男
  const [relationIndex, setRelationIndex] = useState(0); // 默认本人
  const [customRelation, setCustomRelation] = useState('');
  const [showCustomRelation, setShowCustomRelation] = useState(false);

  useEffect(() => {
    // 检查登录状态
    const token = getToken();
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      setShowLoginPopup(true);
      return;
    }
    if (isEdit) {
      loadPatient();
    }
  }, [id]);

  // 登录成功后加载数据
  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
    if (isEdit) {
      loadPatient();
    }
  };

  const loadPatient = async () => {
    try {
      const data = await userApi.getPatientDetail(id!);
      setFormValues(data);
      
      // 设置性别索引
      if (data.gender !== undefined) {
        setGenderIndex(data.gender);
      }
      
      // 设置关系索引
      if (data.relationship) {
        const relIndex = RELATIONSHIP_OPTIONS.indexOf(data.relationship);
        if (relIndex >= 0 && relIndex < RELATIONSHIP_OPTIONS.length - 1) {
          // 在预设选项中
          setRelationIndex(relIndex);
          setShowCustomRelation(false);
        } else {
          // 自定义关系
          setRelationIndex(RELATIONSHIP_OPTIONS.length - 1); // 选中"其他"
          setCustomRelation(data.relationship);
          setShowCustomRelation(true);
        }
      }
    } catch (error) {
      console.error('加载就诊人信息失败', error);
    }
  };

  // 处理性别选择
  const handleGenderChange = (e: any) => {
    const index = parseInt(e.detail.value, 10);
    setGenderIndex(index);
    setFormValues({ ...formValues, gender: GENDER_VALUE_MAP[index] });
  };

  // 处理关系选择
  const handleRelationChange = (e: any) => {
    const index = parseInt(e.detail.value, 10);
    setRelationIndex(index);
    
    if (index === RELATIONSHIP_OPTIONS.length - 1) {
      // 选择"其他"
      setShowCustomRelation(true);
    } else {
      setShowCustomRelation(false);
      setCustomRelation('');
      setFormValues({ ...formValues, relationship: RELATIONSHIP_OPTIONS[index] });
    }
  };

  // 获取当前显示的关系文本
  const getRelationshipText = () => {
    if (showCustomRelation && customRelation) {
      return customRelation;
    }
    if (relationIndex < RELATIONSHIP_OPTIONS.length - 1) {
      return RELATIONSHIP_OPTIONS[relationIndex];
    }
    return '请选择';
  };

  const handleSubmit = async (values: any) => {
    const relationship = showCustomRelation ? customRelation : RELATIONSHIP_OPTIONS[relationIndex];
    
    const formData: PatientFormData = {
      ...formValues,
      ...values,
      gender: GENDER_VALUE_MAP[genderIndex],
      relationship: relationIndex === RELATIONSHIP_OPTIONS.length - 1 && !customRelation 
        ? undefined 
        : relationship,
    };

    if (!formData.name || !formData.phone) {
      Taro.showToast({ title: '请填写完整信息', icon: 'none' });
      return;
    }

    setLoading(true);
    try {
      if (isEdit) {
        await userApi.updatePatient(id!, formData);
      } else {
        await userApi.createPatient(formData);
      }
      Taro.showToast({ title: '保存成功', icon: 'success' });
      Taro.navigateBack();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '保存失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <View className="patient-edit-page">
      <Form
        onFinish={handleSubmit}
      >
        {/* 基本信息卡片 */}
        <View className="form-section">
          <View className="section-title">基本信息</View>
          
          {/* 姓名 - 与其他字段统一的同行布局 */}
          <View className="form-item-row">
            <View className="row-label">
              <Text className="label-text">姓名</Text>
              <Text className="required-mark">*</Text>
            </View>
            <View className="row-input">
              <TaroInput
                className="row-input-field"
                placeholder="请输入真实姓名"
                value={formValues.name || ''}
                onInput={(e) => setFormValues({ ...formValues, name: e.detail.value })}
              />
            </View>
          </View>

          {/* 性别 - Picker 选择 */}
          <View className="form-item-row">
            <View className="row-label">
              <Text className="label-text">性别</Text>
            </View>
            <Picker mode="selector" range={GENDER_OPTIONS} value={genderIndex} onChange={handleGenderChange}>
              <View className="picker-value">
                <Text className={genderIndex === 0 ? 'placeholder' : ''}>{GENDER_OPTIONS[genderIndex]}</Text>
                <Text className="picker-arrow">›</Text>
              </View>
            </Picker>
          </View>

          {/* 身份证号 - 同行布局（选填） */}
          <View className="form-item-row">
            <View className="row-label">
              <Text className="label-text">身份证号</Text>
            </View>
            <View className="row-input">
              <TaroInput
                className="row-input-field row-input-mono"
                placeholder="18位身份证号（选填）"
                maxlength={18}
                value={formValues.idCard || ''}
                onInput={(e) => setFormValues({ ...formValues, idCard: e.detail.value })}
              />
            </View>
          </View>

          {/* 手机号 - 同行布局 */}
          <View className="form-item-row">
            <View className="row-label">
              <Text className="label-text">手机号</Text>
              <Text className="required-mark">*</Text>
            </View>
            <View className="row-input">
              <TaroInput
                className="row-input-field row-input-mono"
                placeholder="请输入11位手机号码"
                type="number"
                maxlength={11}
                value={formValues.phone || ''}
                onInput={(e) => setFormValues({ ...formValues, phone: e.detail.value })}
              />
            </View>
          </View>
        </View>

        {/* 附加设置卡片 */}
        <View className="form-section">
          <View className="section-title">附加设置</View>
          
          {/* 与本人关系 - Picker 选择 */}
          <View className="form-item-row">
            <View className="row-label">
              <Text className="label-text">与本人关系</Text>
            </View>
            <Picker mode="selector" range={RELATIONSHIP_OPTIONS} value={relationIndex} onChange={handleRelationChange}>
              <View className="picker-value">
                <Text className={!formValues.relationship && !showCustomRelation ? 'placeholder' : ''}>
                  {getRelationshipText()}
                </Text>
                <Text className="picker-arrow">›</Text>
              </View>
            </Picker>
          </View>
          
          {/* 自定义关系输入框 */}
          {showCustomRelation && (
            <View className="custom-relation-wrap">
              <TaroInput
                className="custom-input"
                placeholder="请输入与本人关系"
                value={customRelation}
                onInput={(e) => {
                  setCustomRelation(e.detail.value);
                  setFormValues({ ...formValues, relationship: e.detail.value });
                }}
              />
            </View>
          )}

          {/* 设为默认 - 同行布局 */}
          <View className="form-item-row form-item-switch">
            <View className="row-label">
              <Text className="label-text">设为默认就诊人</Text>
            </View>
            <Switch
              checked={formValues.isDefault}
              onChange={(value) => setFormValues({ ...formValues, isDefault: value })}
            />
          </View>
        </View>

        {/* 提示信息 */}
        <View className="form-tip">
          <Text>请确保信息准确，身份证号将用于就诊挂号核验</Text>
        </View>

        <View className="submit-wrap">
          <Button type="primary" block formType="submit" loading={loading}>
            保存
          </Button>
        </View>
      </Form>

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

export default PatientEditPage;
