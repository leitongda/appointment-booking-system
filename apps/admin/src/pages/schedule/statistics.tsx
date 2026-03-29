import { SearchOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Button, Card, Form, Select, DatePicker, Table, Tag, Empty, Row, Col, Statistic } from 'antd';
import { useState } from 'react';
import { useAccess } from '@umijs/max';
import { scheduleApi } from '@hospital/api';
import { useStoreWithPermission } from '@/hooks/useStoreWithPermission';
import type { ScheduleStatisticsItem, ScheduleStatisticsResponse } from '@hospital/api';
import dayjs from 'dayjs';

const ScheduleStatisticsPage: React.FC = () => {
  const [form] = Form.useForm();
  const access = useAccess();
  const { stores } = useStoreWithPermission({ enabledOnly: true });
  const [loading, setLoading] = useState(false);
  const [statistics, setStatistics] = useState<ScheduleStatisticsResponse | null>(null);

  const handleQuery = async () => {
    const values = form.getFieldsValue();
    if (!values.storeId || !values.month) {
      return;
    }

    setLoading(true);
    try {
      const result = await scheduleApi.getStatistics({
        storeId: values.storeId,
        year: values.month.year(),
        month: values.month.month() + 1,
      });
      setStatistics(result);
    } catch (error: any) {
      console.error('查询失败', error);
    } finally {
      setLoading(false);
    }
  };

  // 按日期分组数据
  const groupByDate = (items: ScheduleStatisticsItem[]) => {
    const grouped: Record<string, ScheduleStatisticsItem[]> = {};
    items.forEach(item => {
      if (!grouped[item.scheduleDate]) {
        grouped[item.scheduleDate] = [];
      }
      grouped[item.scheduleDate].push(item);
    });
    return grouped;
  };

  // 计算汇总数据
  const calculateSummary = (items: ScheduleStatisticsItem[]) => {
    let totalMorningSlots = 0;
    let totalAfternoonSlots = 0;
    let totalEveningSlots = 0;
    let totalMorningBooked = 0;
    let totalAfternoonBooked = 0;
    let totalEveningBooked = 0;

    items.forEach(item => {
      totalMorningSlots += item.morningSlots;
      totalAfternoonSlots += item.afternoonSlots;
      totalEveningSlots += item.eveningSlots;
      totalMorningBooked += item.morningBooked;
      totalAfternoonBooked += item.afternoonBooked;
      totalEveningBooked += item.eveningBooked;
    });

    return {
      totalSlots: totalMorningSlots + totalAfternoonSlots + totalEveningSlots,
      totalBooked: totalMorningBooked + totalAfternoonBooked + totalEveningBooked,
      morningSlots: totalMorningSlots,
      afternoonSlots: totalAfternoonSlots,
      eveningSlots: totalEveningSlots,
      morningBooked: totalMorningBooked,
      afternoonBooked: totalAfternoonBooked,
      eveningBooked: totalEveningBooked,
    };
  };

  const columns = [
    {
      title: '日期',
      dataIndex: 'scheduleDate',
      width: 120,
      render: (text: string) => {
        const date = dayjs(text);
        const weekday = ['日', '一', '二', '三', '四', '五', '六'][date.day()];
        return `${text} 周${weekday}`;
      },
    },
    {
      title: '医生',
      dataIndex: 'doctorName',
      width: 100,
    },
    {
      title: '上午',
      children: [
        {
          title: '号源',
          dataIndex: 'morningSlots',
          width: 80,
          render: (val: number) => val || '-',
        },
        {
          title: '已预约',
          dataIndex: 'morningBooked',
          width: 80,
          render: (val: number, record: ScheduleStatisticsItem) => {
            if (!record.morningSlots) return '-';
            const rate = record.morningSlots > 0 ? (val / record.morningSlots * 100).toFixed(0) : 0;
            return (
              <span>
                {val}
                <Tag color={Number(rate) > 80 ? 'red' : Number(rate) > 50 ? 'orange' : 'green'} style={{ marginLeft: 4 }}>
                  {rate}%
                </Tag>
              </span>
            );
          },
        },
      ],
    },
    {
      title: '下午',
      children: [
        {
          title: '号源',
          dataIndex: 'afternoonSlots',
          width: 80,
          render: (val: number) => val || '-',
        },
        {
          title: '已预约',
          dataIndex: 'afternoonBooked',
          width: 80,
          render: (val: number, record: ScheduleStatisticsItem) => {
            if (!record.afternoonSlots) return '-';
            const rate = record.afternoonSlots > 0 ? (val / record.afternoonSlots * 100).toFixed(0) : 0;
            return (
              <span>
                {val}
                <Tag color={Number(rate) > 80 ? 'red' : Number(rate) > 50 ? 'orange' : 'green'} style={{ marginLeft: 4 }}>
                  {rate}%
                </Tag>
              </span>
            );
          },
        },
      ],
    },
    {
      title: '晚间',
      children: [
        {
          title: '号源',
          dataIndex: 'eveningSlots',
          width: 80,
          render: (val: number) => val || '-',
        },
        {
          title: '已预约',
          dataIndex: 'eveningBooked',
          width: 80,
          render: (val: number, record: ScheduleStatisticsItem) => {
            if (!record.eveningSlots) return '-';
            const rate = record.eveningSlots > 0 ? (val / record.eveningSlots * 100).toFixed(0) : 0;
            return (
              <span>
                {val}
                <Tag color={Number(rate) > 80 ? 'red' : Number(rate) > 50 ? 'orange' : 'green'} style={{ marginLeft: 4 }}>
                  {rate}%
                </Tag>
              </span>
            );
          },
        },
      ],
    },
  ];

  const summary = statistics ? calculateSummary(statistics.items) : null;

  return (
    <PageContainer>
      <Card title="查询条件" style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline">
          <Form.Item name="storeId" label="选择门店" rules={[{ required: true }]}>
            <Select
              style={{ width: 200 }}
              placeholder="请选择门店"
              options={stores.map(s => ({ label: s.name, value: s.id }))}
            />
          </Form.Item>
          <Form.Item name="month" label="选择月份" rules={[{ required: true }]}>
            <DatePicker.MonthPicker placeholder="选择月份" />
          </Form.Item>
          <Form.Item>
            <Button 
              type="primary" 
              icon={<SearchOutlined />} 
              onClick={handleQuery}
              loading={loading}
            >
              查询
            </Button>
          </Form.Item>
        </Form>
        <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
          查询流程：选择门店 &gt; 选择月份
        </div>
      </Card>

      {statistics && summary && (
        <>
          <Card title="统计汇总" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={4}>
                <Statistic title="门店" value={statistics.storeName} />
              </Col>
              <Col span={4}>
                <Statistic title="月份" value={`${statistics.year}年${statistics.month}月`} />
              </Col>
              <Col span={4}>
                <Statistic title="总号源" value={summary.totalSlots} />
              </Col>
              <Col span={4}>
                <Statistic title="总预约" value={summary.totalBooked} />
              </Col>
              <Col span={4}>
                <Statistic
                  title="预约率"
                  value={summary.totalSlots > 0 ? (summary.totalBooked / summary.totalSlots * 100).toFixed(1) : 0}
                  suffix="%"
                />
              </Col>
              <Col span={4}>
                <Statistic title="排班天数" value={Object.keys(groupByDate(statistics.items)).length} suffix="天" />
              </Col>
            </Row>
          </Card>

          <Card title="时段统计" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={8}>
                <Statistic title="上午号源" value={summary.morningSlots} />
                <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                  已预约: {summary.morningBooked} ({summary.morningSlots > 0 ? (summary.morningBooked / summary.morningSlots * 100).toFixed(1) : 0}%)
                </div>
              </Col>
              <Col span={8}>
                <Statistic title="下午号源" value={summary.afternoonSlots} />
                <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                  已预约: {summary.afternoonBooked} ({summary.afternoonSlots > 0 ? (summary.afternoonBooked / summary.afternoonSlots * 100).toFixed(1) : 0}%)
                </div>
              </Col>
              <Col span={8}>
                <Statistic title="晚间号源" value={summary.eveningSlots} />
                <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                  已预约: {summary.eveningBooked} ({summary.eveningSlots > 0 ? (summary.eveningBooked / summary.eveningSlots * 100).toFixed(1) : 0}%)
                </div>
              </Col>
            </Row>
          </Card>
        </>
      )}

      <Card title="排班明细">
        {statistics && statistics.items.length > 0 ? (
          <Table
            columns={columns}
            dataSource={statistics.items}
            rowKey={(record) => `${record.scheduleDate}-${record.doctorId}`}
            pagination={{ pageSize: 20 }}
            bordered
            size="small"
            scroll={{ x: 1000 }}
          />
        ) : (
          <Empty description="暂无数据" />
        )}
      </Card>
    </PageContainer>
  );
};

export default ScheduleStatisticsPage;
