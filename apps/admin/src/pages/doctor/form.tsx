import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSelect, ProFormSwitch, ProFormRadio, FooterToolbar } from '@ant-design/pro-components';
import { Card, App, Form, Spin, Button, Space, Typography, Input } from 'antd';
import { useEffect, useState, useRef, useCallback } from 'react';
import { history, useParams, useModel, useAccess } from '@umijs/max';
import { doctorApi, departmentApi, storeApi } from '@hospital/api';
import { PAGINATION_CONFIG } from '@/constants/pagination';
import type { Doctor, Department, Store } from '@hospital/shared';
import ImageUpload from '@/components/ImageUpload';
import RichTextEditor from '@/components/RichTextEditor';
import { debounce } from 'lodash-es';

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

const DoctorFormPage: React.FC = () => {
  const { message } = App.useApp();
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

  const loadDepartments = async () => {
    try {
      const data = await departmentApi.getAll();
      setDepartments(data ?? []);
    } catch (error) {
      console.error('加载科室失败', error);
    }
  };

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

  // 检查用户名是否重复
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

  const loadDoctor = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await doctorApi.getDetailAdmin(id);
      setDoctor(data);
    } catch (error: any) {
      message.error('加载医生信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    // 排除确认密码字段
    const { confirmPassword, ...restValues } = values;
    const data = {
      ...restValues,
      isRecommended: values.isRecommended ? 1 : 0,
      onlineConsultEnabled: values.onlineConsultEnabled ? 1 : 0,
      status: values.status ? 1 : 0,
    };

    try {
      if (isEdit && id) {
        await doctorApi.update(id, data);
        message.success('更新成功');
      } else {
        await doctorApi.create(data);
        message.success('创建成功');
      }
      history.push('/doctor/list');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

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

  // 编辑模式下，等数据加载完再渲染表单（避免 initialValues 警告）
  if (isEdit && loading) {
    return (
      <PageContainer title="编辑医生">
        <Card>
          <div style={{ textAlign: 'center', padding: '50px 0' }}>
            <Spin tip="加载中..."><span /></Spin>
          </div>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer title={isEdit ? '编辑医生' : '新增医生'}>
      <ProForm
        formRef={formRef}
        onFinish={handleSubmit}
        initialValues={initialValues}
        submitter={{
          render: (props) => (
            <FooterToolbar>
              <Space>
                <Button onClick={() => history.back()}>取消</Button>
                <Button type="primary" onClick={() => props.form?.submit()}>
                  {isEdit ? '保存' : '创建'}
                </Button>
              </Space>
            </FooterToolbar>
          ),
        }}
      >
        {/* 基础信息 */}
        <Card title="基础信息" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormText
              name="name"
              label="医生姓名"
              width="md"
              rules={[{ required: true, message: '请输入医生姓名' }]}
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
              rules={[{ required: true, message: '请选择所属门店' }]}
              disabled={!isSuperAdmin && (currentUser?.storeIds?.length ?? 0) <= 1}
              initialValue={!isSuperAdmin && currentStore?.id ? currentStore.id : undefined}
            />
          </ProForm.Group>
          <ProForm.Group>
            <Form.Item
              name="username"
              label="医生账号"
              rules={[{ required: true, message: '请输入医生账号' }]}
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
            {!isEdit && (
              <>
                <ProFormText.Password
                  name="password"
                  label="医生密码"
                  width="md"
                  placeholder="不填则默认为 123456"
                  extra="不填写则使用默认密码：123456"
                  fieldProps={{ autoComplete: 'new-password' }}
                />
                <ProFormText.Password
                  name="confirmPassword"
                  label="确认密码"
                  width="md"
                  placeholder="请再次输入密码"
                  dependencies={['password']}
                  rules={[
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        const password = getFieldValue('password');
                        if (!password && !value) {
                          return Promise.resolve();
                        }
                        if (password && !value) {
                          return Promise.reject(new Error('请再次输入密码'));
                        }
                        if (password !== value) {
                          return Promise.reject(new Error('两次输入的密码不一致'));
                        }
                        return Promise.resolve();
                      },
                    }),
                  ]}
                  fieldProps={{ autoComplete: 'new-password' }}
                />
              </>
            )}
          </ProForm.Group>
          <ProForm.Group>
            <Form.Item
              name="avatar"
              label="医生头像"
              tooltip="1:1比例，推荐尺寸：160px × 160px"
            >
              <ImageUpload
                aspectRatio="1:1"
                folder="doctor"
                placeholder="上传头像"
                width={120}
                height={120}
              />
            </Form.Item>
          </ProForm.Group>
          <ProForm.Group>
            <Form.Item
              name="banner"
              label="医生banner"
              tooltip="16:9比例，若选择医生风格3，请务必上传banner图"
            >
              <ImageUpload
                aspectRatio="16:9"
                folder="doctor"
                placeholder="上传Banner"
                width={272}
                height={153}
              />
            </Form.Item>
          </ProForm.Group>
          <ProForm.Group>
            <ProFormSelect
              name="departmentId"
              label="所属科室"
              width="md"
              options={(departments ?? []).map((d) => ({ label: d.name, value: d.id }))}
              rules={[{ required: true, message: '请选择科室' }]}
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
          <ProFormText name="phone" label="手机号" width="md" />
        </Card>

        {/* 资质信息 */}
        <Card title="资质信息" style={{ marginBottom: 16 }} loading={loading}>
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
          <Form.Item
            name="licenseImage"
            label="执业证书图片"
          >
            <ImageUpload
              aspectRatio="free"
              folder="doctor"
              placeholder="上传证书"
              width={200}
              height={150}
            />
          </Form.Item>
          <ProFormTextArea
            name="honors"
            label="所获荣誉"
            placeholder="如：国家认证的第三批老中医学术继承人"
            fieldProps={{ rows: 3 }}
          />
        </Card>

        {/* 坐诊设置 */}
        <Card title="坐诊设置" style={{ marginBottom: 16 }} loading={loading}>
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
          <ProForm.Group>
            <ProFormSwitch
              name="onlineConsultEnabled"
              label="支持在线问诊"
            />
            <ProFormDigit
              name="onlineConsultFee"
              label="在线问诊费用"
              width="sm"
              min={0}
              addonAfter="元"
            />
          </ProForm.Group>
        </Card>

        {/* 展示设置 */}
        <Card title="展示设置" style={{ marginBottom: 16 }} loading={loading}>
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
        <Card title="其他设置" loading={loading}>
          <ProForm.Group>
            <ProFormDigit
              name="sortOrder"
              label="排序"
              width="sm"
              min={0}
              fieldProps={{ precision: 0 }}
              tooltip="数字越大越靠前"
            />
            <ProFormSwitch name="isRecommended" label="是否推荐" />
            <ProFormSwitch name="status" label="启用状态" />
          </ProForm.Group>
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default DoctorFormPage;
