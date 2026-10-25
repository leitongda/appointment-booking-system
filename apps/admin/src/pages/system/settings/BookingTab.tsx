import {ProForm, ProFormDigit, ProFormSwitch, ProFormSelect} from '@ant-design/pro-components';
import {Card, Space, Row, Col, Select} from 'antd';
import {CalendarOutlined, CloseCircleOutlined, CheckCircleOutlined, NumberOutlined, StopOutlined} from '@ant-design/icons';
import type { BookingTabProps } from './types';
import {DEFAULT_BOOKING_SETTINGS} from './defaults';

const BookingTab: React.FC<BookingTabProps> = ({
  bookingSettings,
  selectedBookingStoreId,
  stores,
  onStoreChange,
  onSubmit,
  canEdit,
}) => (
  <div>
    <div style={{ marginBottom: 24 }}>
      <span style={{ marginRight: 8 }}>选择门店：</span>
      <Select
        style={{ width: 300 }}
        placeholder="全局配置（不选择门店）"
        value={selectedBookingStoreId}
        onChange={onStoreChange}
        options={[
          { label: '全局配置（默认）', value: '' },
          ...stores.map((s) => ({ label: s.name, value: s.id })),
        ]}
      />
    </div>

    <ProForm
      key={selectedBookingStoreId || 'global'}
      onFinish={onSubmit}
      initialValues={{ ...DEFAULT_BOOKING_SETTINGS, ...bookingSettings }}
      submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
      disabled={!canEdit}
    >
      <Space style={{ width: '100%' }} size="large">
        <Card title={<><CalendarOutlined /><span style={{ marginLeft: 8 }}>预约时间限制</span></>} size="small">
          <Row gutter={16}>
            <Col span={8}>
              <ProFormDigit name="advanceDays" label="提前预约天数" min={1} max={30} fieldProps={{ addonAfter: '天' }} tooltip="用户最多可以提前几天进行预约" />
            </Col>
            <Col span={8}>
              <ProFormSwitch name="sameDayBooking" label="允许当天预约" tooltip="是否允许预约当天的号源" />
            </Col>
            <Col span={8}>
              <ProFormDigit name="advanceBookingMinutes" label="预约截止时间" min={0} max={1440} fieldProps={{ addonAfter: '分钟' }} tooltip="预约当天号源的截止时间，0表示不限制" />
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <ProFormSelect
                name="advanceBookingDirection"
                label="时间方向"
                options={[
                  { label: '往前（提前）', value: 'before' },
                  { label: '往后（延后）', value: 'after' },
                ]}
                tooltip="'往前'表示从基准时间往前推算，'往后'表示从基准时间往后推算"
              />
            </Col>
            <Col span={12}>
              <ProFormSelect
                name="advanceBookingReference"
                label="基准时间"
                options={[
                  { label: '开始时间', value: 'start' },
                  { label: '结束时间', value: 'end' },
                ]}
                tooltip="以班次的开始时间还是结束时间作为基准"
              />
            </Col>
          </Row>
        </Card>

        <Card title={<><CloseCircleOutlined /><span style={{ marginLeft: 8 }}>取消规则</span></>} size="small">
          <ProFormDigit name="cancelHours" label="最晚取消时间" min={0} max={168} fieldProps={{ addonAfter: '小时' }} tooltip="用户最晚可以在就诊前几小时取消预约，0表示不限制" />
        </Card>

        <Card title={<><CheckCircleOutlined /><span style={{ marginLeft: 8 }}>签到规则</span></>} size="small">
          <Row gutter={16}>
            <Col span={12}>
              <ProFormDigit name="signInAdvanceMinutes" label="提前签到时间" min={0} max={1440} fieldProps={{ addonAfter: '分钟' }} tooltip="用户最早可以在班次开始前几分钟签到" />
            </Col>
            <Col span={12}>
              <ProFormDigit name="signInLateMinutes" label="迟到签到时间" min={0} max={1440} fieldProps={{ addonAfter: '分钟' }} tooltip="用户最晚可以在班次开始后几分钟签到" />
            </Col>
          </Row>
        </Card>

        <Card title={<><NumberOutlined /><span style={{ marginLeft: 8 }}>频次限制</span></>} size="small">
          <Row gutter={16}>
            <Col span={8}>
              <ProFormDigit name="perDayLimit" label="每人每天最大预约数" min={1} max={10} tooltip="每个用户每天最多可以预约多少次" />
            </Col>
            <Col span={8}>
              <ProFormDigit name="perDoctorLimit" label="每人每医生最大预约数" min={1} max={5} tooltip="每个用户对同一个医生最多可以预约多少次" />
            </Col>
            <Col span={8}>
              <ProFormDigit name="noShowLimit" label="爽约次数限制" min={1} max={10} tooltip="用户爽约多少次后会被限制预约" />
            </Col>
          </Row>
        </Card>

        <Card title={<><StopOutlined /><span style={{ marginLeft: 8 }}>黑名单规则</span></>} size="small">
          <ProFormDigit name="blacklistDays" label="黑名单限制天数" min={1} max={365} fieldProps={{ addonAfter: '天' }} tooltip="用户被加入黑名单后，多少天内无法预约" />
        </Card>

        <Card title={<><CalendarOutlined /><span style={{ marginLeft: 8 }}>通知策略</span></>} size="small">
          <ProFormDigit name="appointmentReminderHours" label="预约提醒提前时间" min={1} max={72} fieldProps={{ addonAfter: '小时' }} tooltip="就诊前多少小时发送预约提醒通知" />
        </Card>
      </Space>
    </ProForm>
  </div>
);

export default BookingTab;
