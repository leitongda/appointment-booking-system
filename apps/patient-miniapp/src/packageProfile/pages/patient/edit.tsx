import { View, Text, Input as TaroInput, Picker, Textarea } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Form, Button, Switch } from '@nutui/nutui-react-taro';
import { useState, useCallback } from 'react';
import { userApi } from '@hospital/api';
import { useProtectedPage } from '../../../hooks/useProtectedPage';
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

// 证件类型选项
const ID_CARD_TYPE_OPTIONS = ['居民身份证', '户口簿', '护照'];

const PatientEditPage = () => {
  const router = useRouter();
  const { id } = router.params;
  const isEdit = !!id;

  const [loading, setLoading] = useState(false);
  const [formValues, setFormValues] = useState<Partial<PatientFormData>>({
    gender: 0,
    isDefault: false,
  });
  
  // 性别和关系选择的索引
  const [genderIndex, setGenderIndex] = useState(0); // 默认未知
  const [relationIndex, setRelationIndex] = useState(0); // 默认本人
  const [customRelation, setCustomRelation] = useState('');
  const [showCustomRelation, setShowCustomRelation] = useState(false);
  const [idCardTypeIndex, setIdCardTypeIndex] = useState(0); // 默认居民身份证
  const [birthday, setBirthday] = useState('');

  const loadPatient = useCallback(async () => {
    if (!isEdit) return;

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

      // 设置证件类型索引
      if (data.idCardType !== undefined) {
        const typeIndex = data.idCardType - 1; // idCardType 从 1 开始
        if (typeIndex >= 0 && typeIndex < ID_CARD_TYPE_OPTIONS.length) {
          setIdCardTypeIndex(typeIndex);
        }
      }

      // 设置出生日期
      if (data.birthday) {
        setBirthday(data.birthday);
      }
    } catch (error) {
      console.error('加载就诊人信息失败', error);
    }
  }, [id, isEdit]);

  const { showLoginPopup, handleLoginSuccess, handleLoginClose } = useProtectedPage({
    load: loadPatient,
    deps: [id],
  });

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

  // 处理证件类型选择
  const handleIdCardTypeChange = (e: any) => {
    const index = parseInt(e.detail.value, 10);
    setIdCardTypeIndex(index);
    setFormValues({ ...formValues, idCardType: index + 1 });
  };

  // 处理出生日期选择
  const handleBirthdayChange = (e: any) => {
    const date = new Date(e.detail.value);
    const formatted = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    setBirthday(formatted);
    setFormValues({ ...formValues, birthday: formatted });
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
      idCardType: idCardTypeIndex + 1,
      birthday: birthday || undefined,
      province: formValues.province || undefined,
      city: formValues.city || undefined,
      district: formValues.district || undefined,
      ethnicity: formValues.ethnicity || undefined,
      address: formValues.address || undefined,
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

  const relationshipText = getRelationshipText();
  const relationshipIsPlaceholder = relationshipText === '请选择';

  return (
    <View className="patient-edit-page">
      <Form
        className="patient-form"
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
            <View className="row-input">
              <Picker mode="selector" range={GENDER_OPTIONS} value={genderIndex} onChange={handleGenderChange}>
                <View className="picker-value">
                  <Text className={genderIndex === 0 ? 'placeholder' : ''}>{GENDER_OPTIONS[genderIndex]}</Text>
                  <Text className="picker-arrow">›</Text>
                </View>
              </Picker>
            </View>
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

          {/* 出生日期 */}
          <View className="form-item-row">
            <View className="row-label">
              <Text className="label-text">出生日期</Text>
            </View>
            <View className="row-input">
              <Picker mode="date" value={birthday || '2000-01-01'} onChange={handleBirthdayChange}>
                <View className="picker-value">
                  <Text className={birthday ? '' : 'placeholder'}>{birthday || '请选择'}</Text>
                  <Text className="picker-arrow">›</Text>
                </View>
              </Picker>
            </View>
          </View>

          {/* 证件类型 */}
          <View className="form-item-row">
            <View className="row-label">
              <Text className="label-text">证件类型</Text>
            </View>
            <View className="row-input">
              <Picker mode="selector" range={ID_CARD_TYPE_OPTIONS} value={idCardTypeIndex} onChange={handleIdCardTypeChange}>
                <View className="picker-value">
                  <Text>{ID_CARD_TYPE_OPTIONS[idCardTypeIndex]}</Text>
                  <Text className="picker-arrow">›</Text>
                </View>
              </Picker>
            </View>
          </View>

          {/* 民族 */}
          <View className="form-item-row">
            <View className="row-label">
              <Text className="label-text">民族</Text>
            </View>
            <View className="row-input">
              <TaroInput
                className="row-input-field"
                placeholder="请输入民族（默认汉族）"
                value={formValues.ethnicity || ''}
                onInput={(e) => setFormValues({ ...formValues, ethnicity: e.detail.value })}
              />
            </View>
          </View>

          {/* 省 */}
          <View className="form-item-row">
            <View className="row-label">
              <Text className="label-text">省</Text>
            </View>
            <View className="row-input">
              <TaroInput
                className="row-input-field"
                placeholder="请输入省份"
                value={formValues.province || ''}
                onInput={(e) => setFormValues({ ...formValues, province: e.detail.value })}
              />
            </View>
          </View>

          {/* 市 */}
          <View className="form-item-row">
            <View className="row-label">
              <Text className="label-text">市</Text>
            </View>
            <View className="row-input">
              <TaroInput
                className="row-input-field"
                placeholder="请输入城市"
                value={formValues.city || ''}
                onInput={(e) => setFormValues({ ...formValues, city: e.detail.value })}
              />
            </View>
          </View>

          {/* 区 */}
          <View className="form-item-row">
            <View className="row-label">
              <Text className="label-text">区</Text>
            </View>
            <View className="row-input">
              <TaroInput
                className="row-input-field"
                placeholder="请输入区县"
                value={formValues.district || ''}
                onInput={(e) => setFormValues({ ...formValues, district: e.detail.value })}
              />
            </View>
          </View>

          {/* 详细地址 */}
          <View className="form-item-row">
            <View className="row-label">
              <Text className="label-text">详细地址</Text>
            </View>
            <View className="row-input">
              <TaroInput
                className="row-input-field"
                placeholder="请输入详细地址"
                value={formValues.address || ''}
                onInput={(e) => setFormValues({ ...formValues, address: e.detail.value })}
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
            <View className="row-input">
              <Picker mode="selector" range={RELATIONSHIP_OPTIONS} value={relationIndex} onChange={handleRelationChange}>
                <View className="picker-value">
                  <Text className={relationshipIsPlaceholder ? 'placeholder' : ''}>
                    {relationshipText}
                  </Text>
                  <Text className="picker-arrow">›</Text>
                </View>
              </Picker>
            </View>
          </View>
          
          {/* 自定义关系输入框 */}
          {showCustomRelation && (
            <View className="custom-relation-wrap">
              <Text className="custom-relation-label">其他关系</Text>
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
          <Button type="primary" block formType="submit" loading={loading} className="submit-btn">
            保存
          </Button>
        </View>
      </Form>

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={handleLoginClose}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default PatientEditPage;
