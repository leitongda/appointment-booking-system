/**
 * 医生表单页面（重构版）
 *
 * 使用基础设施：FormPage、PasswordField、ImageUploadCard、SwitchGroup
 * 保留业务逻辑：账号生成、唯一性验证、门店权限控制
 */
import { ProFormText, ProFormTextArea, ProFormDigit, ProFormSelect, ProFormRadio, ProFormDependency } from '@ant-design/pro-components';
import { Card, Input, Form, Typography } from 'antd';
import { useEffect, useState, useRef, useCallback } from 'react';
import { history, useParams, useModel, useAccess } from '@umijs/max';
import { doctorApi, departmentApi, storeApi } from '@hospital/api';
import { PAGINATION_CONFIG } from '@/constants/pagination';
import type { Doctor, Department, Store } from '@hospital/shared';
import RichTextEditor from '@/components/RichTextEditor';
import { debounce } from 'lodash-es';

// 基础设施导入
import FormPage from '@/components/FormPage';
import { PasswordField, ImageUploadCard, SwitchGroup } from '@/components/formFields';
import { requiredRules, phoneRules, emailRules, stringLengthRules } from '@/utils/formValidators';

const { Text, Link } = Typography;

const GENDER_OPTIONS = [
  { label: '男', value: 1 },
  { label: '女', value: 0 },
];

const PAGE_STYLE_OPTIONS = [
  { label: '风格1', value: 1 },
  { label: '风格2', value: 2 },
  { label: '风格3', value: 3 },
];

const EDUCATION_OPTIONS = [
  { label: '专科', value: '专科' },
  { label: '本科', value: '本科' },
  { label: '硕士', value: '硕士' },
  { label: '博士', value: '博士' },
  { label: '博士后', value: '博士后' },
];

/**
 * 医生表单页面
 */
const DoctorFormPage: React.FC = () => {
  const { id } = useParams();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const { currentUser, currentStore } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [usernameError, setUsernameError] = useState<string>('');
  const [usernameSuggestions, setUsernameSuggestions] = useState<string[]>([]);
  const formRef = useRef<any>(null);

  useEffect(() => {
    loadDepartments();
    loadStores();
    if (isEdit) {
      loadDoctor();
    }
  }, [id]);

  // 加载科室列表
  const loadDepartments = async () => {
    try {
      const data = await departmentApi.getAll();
      setDepartments(data ?? []);
    } catch (error) {
      console.error('加载科室失败', error);
    }
  };

  // 加载门店列表
  const loadStores = async () => {
    try {
      const res = await storeApi.getList({ pageSize: PAGINATION_CONFIG.SELECT_MAX_SIZE, status: 1 });
      let storeList = res.data ?? [];
      // 非超管只显示其关联的门店
      if (!isSuperAdmin && currentUser?.storeIds?.length) {
        storeList = storeList.filter((s) => currentUser.storeIds?.includes(s.id));
      }
      setStores(storeList);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  // 检查用户名是否重复（防抖）
  const checkUsername = useCallback(
    debounce(async (username: string) => {
      if (!username) {
        setUsernameError('');
        setUsernameSuggestions([]);
        return;
      }
      try {
        const res = await doctorApi.checkUsername(username, isEdit ? id : undefined);
        if (res.exists) {
          setUsernameError('该账号已存在');
          setUsernameSuggestions(res.suggestions);
        } else {
          setUsernameError('');
          setUsernameSuggestions([]);
        }
      } catch (error) {
        console.error('检查用户名失败', error);
      }
    }, 500),
    [isEdit, id]
  );

  // 根据姓名自动生成账号
  const handleNameChange = async (name: string) => {
    if (!name || isEdit) return;

    // 只在新增时自动生成
    const currentUsername = formRef.current?.getFieldValue('username');
    if (currentUsername) return; // 如果已有账号则不覆盖

    try {
      const res = await doctorApi.generateUsername(name);
      formRef.current?.setFieldValue('username', res.username);
      setUsernameError('');
      setUsernameSuggestions([]);
    } catch (error) {
      console.error('生成用户名失败', error);
    }
  };

  // 点击推荐账号
  const handleSuggestionClick = (username: string) => {
    formRef.current?.setFieldValue('username', username);
    setUsernameError('');
    setUsernameSuggestions([]);
  };

  // 加载医生详情
  const loadDoctor = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await doctorApi.getDetailAdmin(id);
      setDoctor(data);
    } catch (error) {
      console.error('加载医生信息失败', error);
    } finally {
      setLoading(false);
    }
  };

  // 表单提交处理
  const handleSubmit = async (values: any) => {
    // 排除确认密码字段
    const { confirmPassword, ...restValues } = values;

    // SwitchGroup 自动处理了 boolean ↔ number 转换，这里不需要手动转换
    // 但为了兼容现有逻辑，保留转换
    const data = {
      ...restValues,
      isRecommended: values.isRecommended ? 1 : 0,
      onlineConsultEnabled: values.onlineConsultEnabled ? 1 : 0,
      status: values.status ? 1 : 0,
    };

    try {
      if (isEdit && id) {
        await doctorApi.update(id, data);
      } else {
        await doctorApi.create(data);
      }
      history.push('/doctor/list');
    } catch (error: any) {
      throw error; // 抛出错误，让 FormPage 统一处理
    }
  };

  // 初始值处理
  const initialValues = doctor ? {
    ...doctor,
    isRecommended: doctor.isRecommended === 1,
    onlineConsultEnabled: doctor.onlineConsultEnabled === 1,
    status: doctor.status === 1,
  } : {
    gender: 1,
    yearsOfExperience: 0,
    maxDailyAppointments: 0,
    onlineConsultEnabled: false,
    onlineConsultFee: 0,
    pageStyle: 1,
    sortOrder: 0,
    isRecommended: false,
    status: true,
  };

  return (
    <FormPage
      title={isEdit ? '编辑医生' : '新增医生'}
      loading={loading}
      initialValues={initialValues}
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText={isEdit ? '保存' : '创建'}
      formRef={formRef}
    >
      {/* 基础信息 */}
      <Card title="基础信息" style={{ marginBottom: 16 }}>
        <ProForm.Group>
          <ProFormText
            name="name"
            label="医生姓名"
            width="md"
            rules={[requiredRules('请输入医生姓名')]}
            fieldProps={{
              onBlur: (e) => handleNameChange(e.target.value),
            }}
          />
          <ProFormRadio.Group
            name="gender"
            label="性别"
            options={GENDER_OPTIONS}
          />
          <ProFormSelect
            name="storeId"
            label="所属门店"
            width="md"
            options={(stores ?? []).map((s) => ({ label: s.name, value: s.id }))}
            placeholder="请选择门店"
            rules={[requiredRules('请选择所属门店')]}
            disabled={!isSuperAdmin && (currentUser?.storeIds?.length ?? 0) <= 1}
            initialValue={!isSuperAdmin && currentStore?.id ? currentStore.id : undefined}
          />
        </ProForm.Group>

        {/* 账号输入（带唯一性验证和推荐） */}
        <ProForm.Group>
          <Form.Item
            name="username"
            label="医生账号"
            rules={[requiredRules('请输入医生账号')]}
            validateStatus={usernameError ? 'error' : undefined}
            help={
              usernameError ? (
                <div>
                  <Text type="danger">{usernameError}</Text>
                  {usernameSuggestions.length > 0 && (
                    <div style={{ marginTop: 4 }}>
                      <Text type="secondary">推荐账号：</Text>
                      {usernameSuggestions.map((s, i) => (
                        <Link key={s} onClick={() => handleSuggestionClick(s)} style={{ marginLeft: i > 0 ? 8 : 4 }}>
                          {s}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              ) : undefined
            }
          >
            <Input
              style={{ width: 328 }}
              placeholder="用于医生端登录，输入姓名后自动生成"
              autoComplete="off"
              onChange={(e) => checkUsername(e.target.value)}
            />
          </Form.Item>
        </ProForm.Group>

        {/* 新增模式：使用 PasswordField 组件 */}
        {!isEdit && (
          <PasswordField
            required={false}
            strengthLevel="min"
            showStrengthIndicator={false}
            placeholder="不填则默认为 123456"
            extra="不填写则使用默认密码：123456（如填写需至少6个字符）"
          />
        )}

        {/* 使用 ImageUploadCard 组件 - 头像 */}
        <ImageUploadCard
          title="医生头像"
          name="avatar"
          aspectRatio="1:1"
          width={120}
          height={120}
          folder="doctor"
          placeholder="上传头像"
          tooltip="1:1比例，推荐尺寸：160px × 160px"
        />

        {/* 使用 ImageUploadCard 组件 - Banner */}
        <ImageUploadCard
          title="医生 Banner"
          name="banner"
          aspectRatio="16:9"
          width={272}
          height={153}
          folder="doctor"
          placeholder="上传 Banner"
          tooltip="16:9比例，若选择医生风格3，请务必上传banner图"
        />

        <ProForm.Group>
          <ProFormSelect
            name="departmentId"
            label="所属科室"
            width="md"
            options={(departments ?? []).map((d) => ({ label: d.name, value: d.id }))}
            rules={[requiredRules('请选择科室')]}
          />
          <ProFormText
            name="title"
            label="职称"
            width="md"
            placeholder="如：国家注册中医医师"
          />
          <ProFormDigit
            name="yearsOfExperience"
            label="医龄(年)"
            width="sm"
            min={0}
            fieldProps={{ precision: 0 }}
          />
        </ProForm.Group>
        <ProFormText
          name="phone"
          label="手机号"
          width="md"
          rules={[phoneRules.pattern]}
        />
      </Card>

      {/* 资质信息 */}
      <Card title="资质信息" style={{ marginBottom: 16 }}>
        <ProForm.Group>
          <ProFormSelect
            name="education"
            label="学历"
            width="sm"
            options={EDUCATION_OPTIONS}
            placeholder="请选择"
          />
          <ProFormText
            name="graduateSchool"
            label="毕业院校"
            width="md"
            placeholder="如：重庆市中医大学"
          />
        </ProForm.Group>
        <ProForm.Group>
          <ProFormText
            name="licenseNumber"
            label="执业证书编号"
            width="md"
            placeholder="请输入执业证书编号"
          />
        </ProForm.Group>

        {/* 使用 ImageUploadCard 组件 - 执业证书 */}
        <ImageUploadCard
          title="执业证书图片"
          name="licenseImage"
          aspectRatio="free"
          width={200}
          height={150}
          folder="doctor"
          placeholder="上传证书"
        />

        <ProFormTextArea
          name="honors"
          label="所获荣誉"
          placeholder="如：国家认证的第三批老中医学术继承人"
          fieldProps={{ rows: 3 }}
        />
      </Card>

      {/* 坐诊设置 */}
      <Card title="坐诊设置" style={{ marginBottom: 16 }}>
        <ProFormText
          name="scheduleDesc"
          label="坐诊时间说明"
          width="lg"
          placeholder="如：每周一、三、五上午"
        />
        <ProForm.Group>
          <ProFormDigit
            name="maxDailyAppointments"
            label="每日最大接诊量"
            width="sm"
            min={0}
            fieldProps={{ precision: 0 }}
            tooltip="0表示不限制"
            addonAfter="人"
          />
        </ProForm.Group>

        {/* 在线问诊设置 */}
        <ProFormDependency name={['onlineConsultEnabled']}>
          {({ onlineConsultEnabled }) => (
            <>
              <SwitchGroup
                gutter={16}
                items={[
                  {
                    name: 'onlineConsultEnabled',
                    label: '支持在线问诊',
                    span: 12,
                  },
                ]}
              />
              {onlineConsultEnabled && (
                <ProFormDigit
                  name="onlineConsultFee"
                  label="在线问诊费用"
                  width="sm"
                  min={0}
                  addonAfter="元"
                />
              )}
            </>
          )}
        </ProFormDependency>
      </Card>

      {/* 展示设置 */}
      <Card title="展示设置" style={{ marginBottom: 16 }}>
        <ProForm.Group>
          <ProFormRadio.Group
            name="pageStyle"
            label="页面风格"
            options={PAGE_STYLE_OPTIONS}
            tooltip="选择医生详情页的展示风格"
          />
        </ProForm.Group>
        <ProFormText
          name="promoVideo"
          label="宣传视频"
          width="lg"
          placeholder="视频URL"
        />
        <ProFormText
          name="tags"
          label="标签"
          width="lg"
          placeholder="多个标签用逗号分隔，如：减肥,多囊,失眠"
          tooltip="用于搜索和展示"
        />
        <ProFormTextArea
          name="specialty"
          label="擅长"
          placeholder="医生擅长领域"
          fieldProps={{ rows: 4 }}
        />
        <Form.Item
          name="introduction"
          label="医生介绍"
        >
          <RichTextEditor height={350} placeholder="请输入医生详细介绍..." />
        </Form.Item>
      </Card>

      {/* 其他设置 */}
      <Card title="其他设置">
        <ProForm.Group>
          <ProFormDigit
            name="sortOrder"
            label="排序"
            width="sm"
            min={0}
            fieldProps={{ precision: 0 }}
            tooltip="数字越大越靠前"
          />
        </ProForm.Group>

        {/* 使用 SwitchGroup 组件 */}
        <SwitchGroup
          gutter={16}
          items={[
            {
              name: 'isRecommended',
              label: '是否推荐',
              span: 12,
            },
            {
              name: 'status',
              label: '启用状态',
              span: 12,
            },
          ]}
        />
      </Card>
    </FormPage>
  );
};

export default DoctorFormPage;
