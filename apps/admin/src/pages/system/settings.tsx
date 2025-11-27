import { PageContainer, ProForm, ProFormText, ProFormDigit, ProFormSwitch, ProFormTextArea, ProFormSelect } from '@ant-design/pro-components';
import { Card, Tabs, message, Divider, Alert } from 'antd';

const SettingsPage: React.FC = () => {
  const handleSubmit = async (values: any, type: string) => {
    console.log(`保存${type}设置:`, values);
    message.success('保存成功');
  };

  return (
    <PageContainer>
      <Card>
        <Tabs
          items={[
            {
              key: 'booking',
              label: '预约设置',
              children: (
                <ProForm
                  onFinish={(values) => handleSubmit(values, '预约')}
                  initialValues={{
                    advanceDays: 14,
                    sameDayBooking: true,
                    cancelHours: 2,
                    perDayLimit: 3,
                    perDoctorLimit: 1,
                    noShowLimit: 3,
                    blacklistDays: 30,
                  }}
                >
                  <Alert
                    message="预约规则配置"
                    description="配置患者预约相关的业务规则，修改后立即生效"
                    type="info"
                    showIcon
                    style={{ marginBottom: 24 }}
                  />
                  
                  <Divider orientation="left">预约时间</Divider>
                  <ProFormDigit
                    name="advanceDays"
                    label="可提前预约天数"
                    width="sm"
                    min={1}
                    max={30}
                    tooltip="患者可以提前多少天进行预约"
                    fieldProps={{ addonAfter: '天' }}
                  />
                  <ProFormSwitch
                    name="sameDayBooking"
                    label="允许当天预约"
                    tooltip="是否允许患者预约当天的号源"
                  />
                  <ProFormDigit
                    name="cancelHours"
                    label="就诊前不可取消时间"
                    width="sm"
                    min={0}
                    max={24}
                    tooltip="距离就诊时间多久前不允许取消预约"
                    fieldProps={{ addonAfter: '小时' }}
                  />

                  <Divider orientation="left">预约限制</Divider>
                  <ProFormDigit
                    name="perDayLimit"
                    label="每人每天预约限制"
                    width="sm"
                    min={1}
                    max={10}
                    tooltip="同一患者每天最多可预约的次数"
                    fieldProps={{ addonAfter: '次' }}
                  />
                  <ProFormDigit
                    name="perDoctorLimit"
                    label="每人每医生预约限制"
                    width="sm"
                    min={1}
                    max={5}
                    tooltip="同一患者对同一医生当天最多可预约次数"
                    fieldProps={{ addonAfter: '次' }}
                  />

                  <Divider orientation="left">爽约管理</Divider>
                  <ProFormDigit
                    name="noShowLimit"
                    label="爽约次数限制"
                    width="sm"
                    min={1}
                    max={10}
                    tooltip="爽约多少次后加入黑名单"
                    fieldProps={{ addonAfter: '次' }}
                  />
                  <ProFormDigit
                    name="blacklistDays"
                    label="黑名单禁止天数"
                    width="sm"
                    min={1}
                    max={365}
                    tooltip="加入黑名单后禁止预约的天数"
                    fieldProps={{ addonAfter: '天' }}
                  />
                </ProForm>
              ),
            },
            {
              key: 'hospital',
              label: '医院信息',
              children: (
                <ProForm
                  onFinish={(values) => handleSubmit(values, '医院信息')}
                  initialValues={{
                    hospitalName: '示例医院',
                    hospitalLevel: '三级甲等',
                    address: '北京市朝阳区xxx路xxx号',
                    phone: '010-12345678',
                    workTime: '周一至周日 8:00-17:30',
                  }}
                >
                  <ProFormText name="hospitalName" label="医院名称" rules={[{ required: true }]} width="lg" />
                  <ProFormSelect
                    name="hospitalLevel"
                    label="医院等级"
                    width="md"
                    options={[
                      { label: '三级甲等', value: '三级甲等' },
                      { label: '三级乙等', value: '三级乙等' },
                      { label: '二级甲等', value: '二级甲等' },
                      { label: '二级乙等', value: '二级乙等' },
                      { label: '一级医院', value: '一级医院' },
                    ]}
                  />
                  <ProFormText name="address" label="医院地址" width="lg" />
                  <ProFormText name="phone" label="联系电话" width="md" />
                  <ProFormText name="workTime" label="工作时间" width="md" />
                  <ProFormTextArea name="introduction" label="医院简介" fieldProps={{ rows: 4 }} />
                </ProForm>
              ),
            },
            {
              key: 'wechat',
              label: '微信配置',
              children: (
                <ProForm
                  onFinish={(values) => handleSubmit(values, '微信')}
                >
                  <Alert
                    message="微信小程序配置"
                    description="配置微信小程序的 AppID 和 Secret，用于小程序登录和支付功能"
                    type="info"
                    showIcon
                    style={{ marginBottom: 24 }}
                  />
                  
                  <Divider orientation="left">小程序配置</Divider>
                  <ProFormText name="appId" label="小程序 AppID" width="lg" placeholder="请输入小程序 AppID" />
                  <ProFormText.Password name="appSecret" label="小程序 Secret" width="lg" placeholder="请输入小程序 Secret" />

                  <Divider orientation="left">支付配置</Divider>
                  <ProFormText name="mchId" label="商户号" width="lg" placeholder="请输入微信支付商户号" />
                  <ProFormText.Password name="apiKey" label="API密钥" width="lg" placeholder="请输入 API 密钥" />
                  <ProFormText name="notifyUrl" label="支付回调地址" width="lg" placeholder="https://your-domain.com/api/pay/notify" />
                </ProForm>
              ),
            },
            {
              key: 'sms',
              label: '短信配置',
              children: (
                <ProForm
                  onFinish={(values) => handleSubmit(values, '短信')}
                >
                  <Alert
                    message="短信服务配置"
                    description="配置短信服务商信息，用于发送验证码和预约通知"
                    type="info"
                    showIcon
                    style={{ marginBottom: 24 }}
                  />
                  
                  <ProFormSelect
                    name="smsProvider"
                    label="短信服务商"
                    width="md"
                    options={[
                      { label: '阿里云短信', value: 'aliyun' },
                      { label: '腾讯云短信', value: 'tencent' },
                      { label: '华为云短信', value: 'huawei' },
                    ]}
                  />
                  <ProFormText name="accessKeyId" label="AccessKey ID" width="lg" />
                  <ProFormText.Password name="accessKeySecret" label="AccessKey Secret" width="lg" />
                  <ProFormText name="signName" label="短信签名" width="md" placeholder="如：XX医院" />
                  <ProFormText name="templateCode" label="模板编码" width="md" placeholder="短信模板编码" />
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
