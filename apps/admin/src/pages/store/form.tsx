import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSwitch, ProFormSelect, FooterToolbar } from '@ant-design/pro-components';
import type { ProFormInstance } from '@ant-design/pro-components';
import { Card, App, Row, Col, Form, Spin, Button, Space } from 'antd';
import { useEffect, useState, useRef, useCallback } from 'react';
import { history, useParams } from '@umijs/max';
import { storeApi } from '@hospital/api';
import type { Store } from '@hospital/shared';
import ImageUpload from '@/components/ImageUpload';
import MapLocationPicker from '@/components/MapLocationPicker';
import type { LocationInfo } from '@/components/MapLocationPicker';
import { pinyin } from 'pinyin-pro';

// 风格选项 - 中国风主题预设
const THEME_STYLE_OPTIONS = [
  { label: '🔴 中医-红（朱砂红）', value: '中医-红' },
  { label: '🟢 中医-绿（翡翠绿）', value: '中医-绿' },
  { label: '🔵 现代-蓝（琉璃蓝）', value: '现代-蓝' },
  { label: '⚪ 简约-白（玄墨灰）', value: '简约-白' },
  { label: '🏯 故宫红（宫墙红）', value: '故宫红' },
  { label: '🏺 青花瓷（钴蓝）', value: '青花瓷' },
  { label: '🍵 茶韵（茶褐）', value: '茶韵' },
  { label: '👑 紫禁（帝王紫）', value: '紫禁' },
];

// 防抖函数
function debounce<T extends (...args: any[]) => any>(fn: T, delay: number) {
  let timer: NodeJS.Timeout | null = null;
  return (...args: Parameters<T>) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// 根据名称生成编码（拼音首字母 + 4位随机数）
const generateCodeFromName = (name: string): string => {
  if (!name) return '';
  // 获取拼音首字母
  const pinyinResult = pinyin(name, { pattern: 'first', toneType: 'none' });
  const initials = pinyinResult.replace(/\s/g, '').toUpperCase();
  // 生成4位随机数
  const randomNum = Math.floor(1000 + Math.random() * 9000);
  return `${initials}${randomNum}`;
};

const StoreFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [store, setStore] = useState<Store | null>(null);
  const formRef = useRef<ProFormInstance>();
  // 标记编码是否被用户手动修改过
  const [codeManuallyEdited, setCodeManuallyEdited] = useState(false);

  // 处理地图选点后的位置变化
  const handleLocationChange = (location: LocationInfo) => {
    formRef.current?.setFieldsValue({
      province: location.province,
      city: location.city,
      district: location.district,
      address: location.address || location.formattedAddress,
      longitude: location.longitude,
      latitude: location.latitude,
    });
  };

  useEffect(() => {
    if (isEdit) {
      loadStore();
      // 编辑模式下，认为编码已被手动设置
      setCodeManuallyEdited(true);
    }
  }, [id]);

  const loadStore = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await storeApi.getDetail(id);
      setStore(data);
    } catch (error: any) {
      message.error('加载门店信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      // 排除确认密码字段
      const { confirmPassword, ...restValues } = values;
      const data = {
        ...restValues,
        status: values.status ? 1 : 0
      };

      if (isEdit && id) {
        await storeApi.update(id, data);
        message.success('更新成功');
      } else {
        await storeApi.create(data);
        message.success('创建成功');
      }
      history.push('/store/list');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  // 名称变化时自动生成编码
  const handleNameChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const name = e.target.value;
    // 只有在新增模式且编码未被手动修改时才自动生成
    if (!isEdit && !codeManuallyEdited && name) {
      const code = generateCodeFromName(name);
      formRef.current?.setFieldsValue({ code });
    }
  }, [isEdit, codeManuallyEdited]);

  // 编码输入框获得焦点时，标记为手动编辑
  const handleCodeFocus = () => {
    if (!isEdit) {
      setCodeManuallyEdited(true);
    }
  };

  // 异步验证名称唯一性（带防抖）
  const validateNameUnique = useCallback(
    debounce(async (name: string, resolve: (msg?: string) => void) => {
      if (!name) {
        resolve();
        return;
      }
      try {
        const { exists } = await storeApi.checkUnique('name', name, isEdit ? id : undefined);
        if (exists) {
          resolve('该门店名称已存在');
        } else {
          resolve();
        }
      } catch {
        resolve(); // 验证失败时不阻止提交
      }
    }, 500),
    [isEdit, id]
  );

  // 异步验证编码唯一性（带防抖）
  const validateCodeUnique = useCallback(
    debounce(async (code: string, resolve: (msg?: string) => void) => {
      if (!code) {
        resolve();
        return;
      }
      try {
        const { exists } = await storeApi.checkUnique('code', code, isEdit ? id : undefined);
        if (exists) {
          resolve('该门店编码已存在');
        } else {
          resolve();
        }
      } catch {
        resolve();
      }
    }, 500),
    [isEdit, id]
  );

  const initialValues = store ? {
    ...store,
    status: store.status === 1
  } : {
    status: true,
    sortOrder: 0,
    themeStyle: '中医-红',
    maxCardsPerUser: 5,
    openingTime: '08:00',
    closingTime: '18:00',
  };

  // 地图初始位置
  const initialLocation: LocationInfo | undefined = store?.longitude && store?.latitude ? {
    longitude: store.longitude,
    latitude: store.latitude,
    province: store.province,
    city: store.city,
    district: store.district,
    address: store.address,
  } : undefined;

  // 编辑模式下，等数据加载完再渲染表单（避免 initialValues 警告）
  if (isEdit && loading) {
    return (
      <PageContainer title="编辑门店">
        <Card>
          <div style={{ textAlign: 'center', padding: '50px 0' }}>
            <Spin tip="加载中..."><span /></Spin>
          </div>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer title={isEdit ? '编辑门店' : '新增门店'}>
      <ProForm
        formRef={formRef}
        onFinish={handleSubmit}
        initialValues={initialValues}
        submitter={{
          render: (props, dom) => (
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
              label="门店名称"
              width="md"
              rules={[
                { required: true, message: '请输入门店名称' },
                { max: 100, message: '门店名称不能超过100个字符' },
                {
                  validator: (_, value) => new Promise((resolve, reject) => {
                    if (!value) {
                      resolve(undefined);
                      return;
                    }
                    validateNameUnique(value, (msg) => {
                      if (msg) reject(new Error(msg));
                      else resolve(undefined);
                    });
                  }),
                },
              ]}
              placeholder="如：xxx医馆"
              fieldProps={{
                onChange: handleNameChange,
              }}
            />
            <ProFormText
              name="code"
              label="门店编码"
              width="md"
              rules={[
                { required: true, message: '请输入门店编码' },
                { pattern: /^[A-Za-z0-9_]{2,50}$/, message: '编码只能包含字母、数字、下划线，2-50字符' },
                {
                  validator: (_, value) => new Promise((resolve, reject) => {
                    if (!value) {
                      resolve(undefined);
                      return;
                    }
                    validateCodeUnique(value, (msg) => {
                      if (msg) reject(new Error(msg));
                      else resolve(undefined);
                    });
                  }),
                },
              ]}
              placeholder="输入名称后自动生成，可手动修改"
              extra="输入门店名称后自动生成，也可手动修改"
              fieldProps={{
                onFocus: handleCodeFocus,
              }}
            />
          </ProForm.Group>
          <ProForm.Group>
            <ProFormText
              name="contactPerson"
              label="联系人"
              width="md"
              placeholder="如：张经理"
              rules={[{ max: 50, message: '联系人不能超过50个字符' }]}
            />
            <ProFormText
              name="phone"
              label="联系方式"
              width="md"
              placeholder="如：138xxxx8888"
              rules={[{ pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号' }]}
              fieldProps={{ autoComplete: 'off' }}
            />
          </ProForm.Group>
          <ProForm.Group>
            <ProFormText
              name="email"
              label="邮箱"
              width="md"
              placeholder="如：example@qq.com"
              rules={[{ type: 'email', message: '请输入正确的邮箱地址' }]}
              fieldProps={{ autoComplete: 'off' }}
            />
          </ProForm.Group>
        </Card>

        {/* 账号设置 */}
        <Card title="账号设置" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormText.Password
              name="password"
              label="门店密码"
              width="md"
              placeholder="不填则默认为 123456"
              extra="不填写则使用默认密码：123456"
              fieldProps={{ autoComplete: 'new-password' }}
              rules={[
                { min: 6, message: '密码至少6个字符' },
                { max: 50, message: '密码不能超过50个字符' },
              ]}
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
          </ProForm.Group>
        </Card>

        {/* 地址信息 */}
        <Card title="地址信息" style={{ marginBottom: 16 }} loading={loading}>
          <Form.Item label="地图选点" tooltip="在地图上点击选点或搜索地址，将自动填充下方位置信息">
            <MapLocationPicker
              value={initialLocation}
              onChange={handleLocationChange}
              height={400}
              placeholder="搜索地址，如：xxx中医馆"
            />
          </Form.Item>
          
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={8}>
              <ProFormText
                name="province"
                label="省份"
                placeholder="通过地图选点自动填充"
                fieldProps={{ readOnly: true }}
              />
            </Col>
            <Col span={8}>
              <ProFormText
                name="city"
                label="城市"
                placeholder="通过地图选点自动填充"
                fieldProps={{ readOnly: true }}
              />
            </Col>
            <Col span={8}>
              <ProFormText
                name="district"
                label="区/县"
                placeholder="通过地图选点自动填充"
                fieldProps={{ readOnly: true }}
              />
            </Col>
          </Row>
          
          <ProFormTextArea
            name="address"
            label="详细地址"
            placeholder="通过地图选点自动填充，也可手动修改"
            fieldProps={{ rows: 2 }}
            rules={[{ max: 255, message: '详细地址不能超过255个字符' }]}
          />
          
          <Row gutter={16}>
            <Col span={12}>
              <ProFormText
                name="longitude"
                label="经度"
                placeholder="通过地图选点自动填充"
                fieldProps={{ readOnly: true }}
              />
            </Col>
            <Col span={12}>
              <ProFormText
                name="latitude"
                label="纬度"
                placeholder="通过地图选点自动填充"
                fieldProps={{ readOnly: true }}
              />
            </Col>
          </Row>
        </Card>

        {/* 展示设置 */}
        <Card title="展示设置" style={{ marginBottom: 16 }} loading={loading}>
          <Form.Item
            name="logo"
            label="Logo"
            tooltip="1:1比例，推荐尺寸：160px × 160px"
          >
            <ImageUpload
              aspectRatio="1:1"
              folder="store"
              placeholder="上传Logo"
              width={120}
              height={120}
            />
          </Form.Item>
          <ProForm.Group>
            <ProFormSelect
              name="themeStyle"
              label="风格选择"
              width="sm"
              options={THEME_STYLE_OPTIONS}
              placeholder="请选择风格"
            />
            <ProFormDigit
              name="sortOrder"
              label="排序"
              width="xs"
              min={0}
              fieldProps={{ precision: 0 }}
              tooltip="数字越大越靠前"
            />
          </ProForm.Group>
        </Card>

        {/* 营业设置 */}
        <Card title="营业设置" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormText
              name="openingTime"
              label="开始营业时间"
              width="sm"
              placeholder="如：08:00"
              rules={[
                { pattern: /^([01]\d|2[0-3]):([0-5]\d)$/, message: '请输入正确的时间格式 HH:mm' },
              ]}
            />
            <ProFormText
              name="closingTime"
              label="结束营业时间"
              width="sm"
              placeholder="如：18:00"
              rules={[
                { pattern: /^([01]\d|2[0-3]):([0-5]\d)$/, message: '请输入正确的时间格式 HH:mm' },
              ]}
            />
            <ProFormSwitch name="status" label="营业状态" />
          </ProForm.Group>
        </Card>

        {/* 就诊卡配置 */}
        <Card title="就诊卡配置" style={{ marginBottom: 16 }} loading={loading}>
          <ProFormDigit
            name="maxCardsPerUser"
            label="每用户可建就诊卡数量上限"
            width="sm"
            min={1}
            max={20}
            fieldProps={{ precision: 0 }}
            placeholder="默认5张"
            tooltip="限制该门店下每个用户可绑定的就诊卡数量"
            extra="设置范围：1-20，默认为5张"
          />
        </Card>

        {/* 其他信息 */}
        <Card title="其他信息" loading={loading}>
          <ProFormTextArea
            name="description"
            label="门店简介"
            placeholder="请输入门店简介"
            fieldProps={{ rows: 3 }}
          />
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default StoreFormPage;
