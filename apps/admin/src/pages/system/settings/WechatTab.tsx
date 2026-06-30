import { ProForm, ProFormText } from '@ant-design/pro-components';
import { Typography, Select, Spin } from 'antd';
import type { WechatTabProps } from './types';

const { Text } = Typography;

const WechatTab: React.FC<WechatTabProps> = ({
  selectedStoreId,
  stores,
  storeWechatConfig,
  wechatLoading,
  onStoreChange,
  onSubmit,
  canEdit,
}) => (
  <div>
    <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
      每个门店可以配置独立的微信小程序。请先选择门店，然后配置对应的 AppID 和 Secret。在{' '}
      <a href="https://mp.weixin.qq.com" target="_blank" rel="noopener noreferrer">
        微信公众平台
      </a>{' '}
      → 开发管理 → 开发设置 中获取。
    </Text>

    <div style={{ marginBottom: 24 }}>
      <span style={{ marginRight: 8 }}>选择门店：</span>
      <Select
        style={{ width: 300 }}
        placeholder="请选择门店"
        value={selectedStoreId || undefined}
        onChange={onStoreChange}
        options={stores.map((s) => ({ label: s.name, value: s.id }))}
        allowClear
      />
    </div>

    {selectedStoreId ? (
      <Spin spinning={wechatLoading}>
        <ProForm
          key={selectedStoreId}
          onFinish={onSubmit}
          initialValues={storeWechatConfig || {}}
          submitter={{
            searchConfig: { submitText: '保存设置' },
            resetButtonProps: { style: { display: 'none' } },
            submitButtonProps: { disabled: !canEdit },
          }}
        >
          <ProFormText
            name="appId"
            label="小程序 AppID"
            placeholder="请输入小程序 AppID"
            rules={[{ required: true, message: '请输入小程序 AppID' }]}
            extra="在微信公众平台 → 开发管理 → 开发设置 中获取"
            disabled={!canEdit}
          />
          <ProFormText.Password
            name="appSecret"
            label="小程序 Secret"
            placeholder="请输入小程序 Secret"
            rules={[{ required: true, message: '请输入小程序 Secret' }]}
            extra="Secret 是敏感信息，请妥善保管（已保存的密钥显示为 ******）"
            fieldProps={{ autoComplete: 'new-password' }}
            disabled={!canEdit}
          />
          <ProFormText
            name="mchId"
            label="商户号 (选填)"
            placeholder="请输入微信支付商户号"
            extra="如需使用微信支付功能，请填写商户号"
            disabled={!canEdit}
          />
          <ProFormText.Password
            name="apiKey"
            label="API 密钥 (选填)"
            placeholder="请输入微信支付 API 密钥"
            extra="如需使用微信支付功能，请填写 API 密钥"
            fieldProps={{ autoComplete: 'new-password' }}
            disabled={!canEdit}
          />
          <ProFormText
            name="notifyUrl"
            label="支付回调地址 (选填)"
            placeholder="如：https://your-domain.com/api/v1/wechat/pay/notify"
            extra="微信支付结果通知的回调地址"
            disabled={!canEdit}
          />
          {!canEdit && (
            <Text type="warning" style={{ display: 'block', marginTop: 16 }}>
              您没有修改微信配置的权限，仅可查看
            </Text>
          )}
        </ProForm>
      </Spin>
    ) : (
      <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
        请先选择门店以查看或编辑微信配置
      </div>
    )}
  </div>
);

export default WechatTab;
