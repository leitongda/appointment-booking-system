import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormSelect, FooterToolbar } from '@ant-design/pro-components';
import { Card, App, Button, Space } from 'antd';
import { history } from '@umijs/max';
import { messageApi } from '@hospital/api';

const TYPE_OPTIONS = [
  { label: '系统', value: 'system' },
  { label: '预约', value: 'appointment' },
  { label: '提醒', value: 'reminder' },
  { label: '公告', value: 'notice' },
];

const MessageFormPage: React.FC = () => {
  const { message } = App.useApp();

  const handleSubmit = async (values: any) => {
    try {
      await messageApi.send({
        userId: values.userId,
        userType: values.userType,
        title: values.title,
        content: values.content,
        messageType: values.messageType,
      });
      message.success('发送成功');
      history.push('/content-center/message');
    } catch (error: any) {
      message.error(error.message || '发送失败');
    }
  };

  return (
    <PageContainer title="发送消息">
      <ProForm
        onFinish={handleSubmit}
        initialValues={{ userType: 'patient', messageType: 'system' }}
        submitter={{
          render: (props, _dom) => (
            <FooterToolbar>
              <Space>
                <Button onClick={() => history.back()}>取消</Button>
                <Button type="primary" onClick={() => props.form?.submit()}>
                  发送
                </Button>
              </Space>
            </FooterToolbar>
          ),
        }}
      >
        <Card title="消息信息">
          <ProForm.Group>
            <ProFormText
              name="userId"
              label="用户ID"
              width="md"
              rules={[{ required: true, message: '请输入用户ID' }]}
            />
            <ProFormSelect
              name="userType"
              label="用户类型"
              width="md"
              options={[
                { label: '患者', value: 'patient' },
                { label: '医生', value: 'doctor' },
              ]}
              rules={[{ required: true, message: '请选择用户类型' }]}
            />
          </ProForm.Group>
          <ProFormSelect
            name="messageType"
            label="消息类型"
            width="md"
            options={TYPE_OPTIONS}
          />
          <ProFormText
            name="title"
            label="标题"
            width="lg"
            rules={[{ required: true, message: '请输入标题' }]}
          />
          <ProFormTextArea
            name="content"
            label="内容"
            placeholder="请输入消息内容"
            fieldProps={{ rows: 6 }}
          />
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default MessageFormPage;

