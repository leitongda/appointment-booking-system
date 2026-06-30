import { Table, Switch } from 'antd';
import type { BookingFieldConfig } from '@hospital/api';
import type { BookingFieldsTabProps } from './types';

const BookingFieldsTab: React.FC<BookingFieldsTabProps> = ({
  bookingFields,
  onFieldChange,
  canEdit,
}) => {
  const columns = [
    { title: '预约选项名称', dataIndex: 'name', width: 150 },
    {
      title: '状态',
      dataIndex: 'enabled',
      width: 120,
      render: (_: any, record: BookingFieldConfig) => (
        <Switch
          checked={record.enabled}
          checkedChildren="启用"
          unCheckedChildren="禁用"
          disabled={!canEdit}
          onChange={(checked) => onFieldChange(record.field, 'enabled', checked)}
        />
      ),
    },
    {
      title: '必填/非必填',
      dataIndex: 'required',
      width: 120,
      render: (_: any, record: BookingFieldConfig) => (
        <Switch
          checked={record.required}
          checkedChildren="必填"
          unCheckedChildren="非必填"
          disabled={!record.enabled || !canEdit}
          onChange={(checked) => onFieldChange(record.field, 'required', checked)}
        />
      ),
    },
    { title: '操作', width: 80, render: () => '-' },
  ];

  return (
    <Table
      columns={columns}
      dataSource={bookingFields}
      rowKey="field"
      pagination={false}
      size="middle"
    />
  );
};

export default BookingFieldsTab;
