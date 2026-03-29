/**
 * 门店表单页面（重构版）
 *
 * 使用基础设施：FormPage、ImageUploadCard、SwitchGroup
 * 保留业务逻辑：编码生成、唯一性验证、时间格式处理
 */
import { ProForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSelect } from '@ant-design/pro-components';
import { Card } from 'antd';
import { useEffect, useState, useRef, useCallback } from 'react';
import { history, useParams } from '@umijs/max';
import { storeApi } from '@hospital/api';
import type { Store } from '@hospital/shared';
import { pinyin } from 'pinyin-pro';
import { debounce } from 'lodash-es';

// 基础设施导入
import FormPage from '@/components/FormPage';
import { ImageUploadCard, SwitchGroup } from '@/components/formFields';
import { requiredRules, phoneOrLandlineRules, emailRules, stringLengthRules, codeRules, timeRules, combinedRules } from '@/utils/formValidators';

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

/**
 * 根据名称生成编码（拼音首字母 + 4位随机数）
 */
const generateCodeFromName = (name: string): string => {
  if (!name) return '';
  // 获取拼音首字母
  const pinyinResult = pinyin(name, { pattern: 'first', toneType: 'none' });
  const initials = pinyinResult.replace(/\s/g, '').toUpperCase();
  // 生成4位随机数
  const randomNum = Math.floor(1000 + Math.random() * 9000);
  return `${initials}${randomNum}`;
};

/**
 * 门店表单页面
 */
const StoreFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [store, setStore] = useState<Store | null>(null);
  const formRef = useRef<any>();
  // 标记编码是否被用户手动修改过
  const [codeManuallyEdited, setCodeManuallyEdited] = useState(false);

  useEffect(() => {
    if (isEdit) {
      loadStore();
      // 编辑模式下，认为编码已被手动设置
      setCodeManuallyEdited(true);
    }
  }, [id]);

  // 加载门店详情
  const loadStore = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await storeApi.getDetail(id);
      setStore(data);
    } catch (error) {
      console.error('加载门店信息失败', error);
    } finally {
      setLoading(false);
    }
  };

  // 表单提交处理
  const handleSubmit = async (values: any) => {
    try {
      // SwitchGroup 自动处理了 boolean ↔ number 转换，但为了兼容现有逻辑，保留转换
      const data = {
        ...values,
        status: values.status ? 1 : 0
      };

      if (isEdit && id) {
        await storeApi.update(id, data);
      } else {
        await storeApi.create(data);
      }
      history.push('/organization/store/list');
    } catch (error) {
      throw error; // 抛出错误，让 FormPage 统一处理
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

  // 格式化时间，从 HH:mm:ss 转换为 HH:mm
  const formatTime = (time: string | undefined): string | undefined => {
    if (!time) return undefined;
    return time.slice(0, 5); // 取前5个字符 "HH:mm"
  };

  // 初始值处理
  const initialValues = store ? {
    ...store,
    openingTime: formatTime(store.openingTime),
    closingTime: formatTime(store.closingTime),
    status: store.status === 1
  } : {
    status: true,
    sortOrder: 0,
    themeStyle: '中医-红',
    maxCardsPerUser: 5,
    openingTime: '08:00',
    closingTime: '18:00',
  };

  return (
    <FormPage
      title={isEdit ? '编辑门店' : '新增门店'}
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
            label="门店名称"
            width="md"
            rules={combinedRules(
              requiredRules('请输入门店名称'),
              stringLengthRules(1, 100),
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
            )}
            placeholder="如：xxx医馆"
            fieldProps={{
              onChange: handleNameChange,
            }}
          />
          <ProFormText
            name="code"
            label="门店编码"
            width="md"
            rules={combinedRules(
              requiredRules('请输入门店编码'),
              codeRules('slug').pattern,
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
            )}
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
            rules={[stringLengthRules(0, 50)]}
          />
          <ProFormText
            name="phone"
            label="联系方式"
            width="md"
            placeholder="如：138xxxx8888 或 xxxx-xxxxxxxx"
            rules={[phoneOrLandlineRules.pattern]}
            fieldProps={{ autoComplete: 'off' }}
          />
        </ProForm.Group>
        <ProForm.Group>
          <ProFormText
            name="email"
            label="邮箱"
            width="md"
            placeholder="如：example@qq.com"
            rules={[emailRules]}
            fieldProps={{ autoComplete: 'off' }}
          />
        </ProForm.Group>
      </Card>

      {/* 地址信息 */}
      <Card title="地址信息" style={{ marginBottom: 16 }}>
        <ProFormTextArea
          name="address"
          label="地址"
          placeholder="请输入完整地址，如：贵州省贵阳市观山湖区XX路XX号XX大厦X楼"
          fieldProps={{ rows: 3 }}
          rules={combinedRules(
            requiredRules('请输入地址'),
            stringLengthRules(1, 255)
          )}
          extra="请输入完整的机构地址，包含省市区、街道、门牌号等信息"
        />
      </Card>

      {/* 展示设置 */}
      <Card title="展示设置" style={{ marginBottom: 16 }}>
        {/* 使用 ImageUploadCard 组件 - Logo */}
        <ImageUploadCard
          title="Logo"
          name="logo"
          aspectRatio="free"
          width={120}
          height={120}
          folder="store"
          placeholder="上传Logo"
          tooltip="支持自由剪裁，推荐尺寸：160px × 160px"
        />

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
      <Card title="营业设置" style={{ marginBottom: 16 }}>
        <ProForm.Group>
          <ProFormText
            name="openingTime"
            label="开始营业时间"
            width="sm"
            placeholder="如：08:00"
            rules={[timeRules.pattern]}
          />
          <ProFormText
            name="closingTime"
            label="结束营业时间"
            width="sm"
            placeholder="如：18:00"
            rules={[timeRules.pattern]}
          />
        </ProForm.Group>

        {/* 使用 SwitchGroup 组件 */}
        <SwitchGroup
          gutter={16}
          items={[
            {
              name: 'status',
              label: '营业状态',
              span: 12,
            },
          ]}
        />
      </Card>

      {/* 就诊卡配置 */}
      <Card title="就诊卡配置" style={{ marginBottom: 16 }}>
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
      <Card title="其他信息">
        <ProFormTextArea
          name="description"
          label="门店简介"
          placeholder="请输入门店简介"
          fieldProps={{ rows: 15 }}
        />
      </Card>
    </FormPage>
  );
};

export default StoreFormPage;
