import { PageContainer, ProForm, ProFormText, ProFormDigit, ProFormSwitch } from '@ant-design/pro-components';
import { Card, Tabs, message } from 'antd';

const SettingsPage: React.FC = () => {
  return (
    <PageContainer>
      <Card>
        <Tabs
          items={[
            {
              key: 'booking',
              label: '预约设置',
              children: (
                <ProForm onFinish={async (values) => { message.success('保存成功'); }}>
                  <ProFormDigit name="advanceDays" label="可提前预约天数" width="sm" min={1} max={30} initialValue={14} />
                  <ProFormSwitch name="sameDay" label="允许当天预约" initialValue={true} />
                  <ProFormDigit name="cancelHours" label="就诊前不可取消时间(小时)" width="sm" min={0} max={24} initialValue={2} />
                  <ProFormDigit name="perDayLimit" label="每人每天预约限制" width="sm" min={1} max={10} initialValue={3} />
                  <ProFormDigit name="noShowLimit" label="爽约次数进入黑名单" width="sm" min={1} max={10} initialValue={3} />
                </ProForm>
              ),
            },
            {
              key: 'wechat',
              label: '微信设置',
              children: (
                <ProForm onFinish={async (values) => { message.success('保存成功'); }}>
                  <ProFormText name="appId" label="小程序 AppID" width="lg" />
                  <ProFormText.Password name="appSecret" label="小程序 Secret" width="lg" />
                  <ProFormText name="mchId" label="商户号" width="lg" />
                  <ProFormText.Password name="apiKey" label="支付密钥" width="lg" />
                </ProForm>
              ),
            },
          ]}
        />
      </Card>
    </PageContainer>
  );
};

export default SettingsPage;

