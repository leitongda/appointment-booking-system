import { Modal, Button, Space, Alert, Table, InputNumber, Tabs, Tag, Tooltip } from 'antd';
import { EyeOutlined, CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { ProForm, ProFormDatePicker } from '@ant-design/pro-components';
import type { ProFormInstance } from '@ant-design/pro-components';
import type { ScheduleTemplate, SchedulePreviewGenerateResponse } from '@hospital/shared';
import { WEEKDAY_MAP } from '@hospital/shared';
import dayjs from 'dayjs';

interface GenerateScheduleModalProps {
  open: boolean;
  onCancel: () => void;
  onGenerate: (values: any) => Promise<boolean>;
  onPreview: () => Promise<void>;
  onConfirmGenerate: () => Promise<void>;
  formRef?: React.RefObject<ProFormInstance>;
  currentTemplate?: ScheduleTemplate | null;
  selectedTemplates: string[];
  previewData: SchedulePreviewGenerateResponse[];
  showPreview: boolean;
  previewLoading: boolean;
  generateLoading: boolean;
  editedCapacities: Record<string, number>;
  onCapacityChange: (key: string, value: number) => void;
}

const GenerateScheduleModal: React.FC<GenerateScheduleModalProps> = ({
  open,
  onCancel,
  onGenerate,
  onPreview,
  onConfirmGenerate,
  formRef,
  currentTemplate,
  selectedTemplates,
  previewData,
  showPreview,
  previewLoading,
  generateLoading,
  editedCapacities,
  onCapacityChange,
}) => {
  return (
    <Modal
      title={currentTemplate ? `生成排班 - ${currentTemplate.name}` : '根据规则生成排班'}
      open={open}
      onCancel={onCancel}
      footer={showPreview ? (
        <Space>
          <Button onClick={() => onCancel()} disabled={generateLoading}>返回设置</Button>
          <Button type="primary" onClick={onConfirmGenerate} loading={generateLoading}>
            确认生成 ({previewData.reduce((acc, p) => acc + p.totalCount, 0)} 条)
          </Button>
        </Space>
      ) : (
        <Space>
          <Button onClick={() => onCancel()} disabled={generateLoading}>取消</Button>
          <Button
            icon={<EyeOutlined />}
            onClick={onPreview}
            loading={previewLoading}
            disabled={generateLoading}
          >
            预览班次
          </Button>
          <Button type="primary" onClick={() => formRef?.current?.submit()} loading={generateLoading}>
            直接生成
          </Button>
        </Space>
      )}
      destroyOnHidden
      width={showPreview ? 900 : 500}
    >
      {!showPreview ? (
        <ProForm
          formRef={formRef}
          onFinish={onGenerate}
          submitter={false}
        >
          {currentTemplate ? (
            <Alert
              message={
                <div>
                  <div>规则：<strong>{currentTemplate.name}</strong></div>
                  <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                    医生：{currentTemplate.doctorName} | 科室：{currentTemplate.departmentName} |
                    星期：{(currentTemplate.weekdays || []).map((w: number) => WEEKDAY_MAP[w]).join('、')}
                    {currentTemplate.breakTimes && currentTemplate.breakTimes.length > 0 && (
                      <span> | 排除时间：{currentTemplate.breakTimes.map(bt => `${bt.startTime}-${bt.endTime}`).join('、')}</span>
                    )}
                  </div>
                </div>
              }
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
          ) : (
            <Alert
              message={`已选择 ${selectedTemplates.length} 个规则`}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          {/* 快捷选择按钮 */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 8, color: '#666' }}>快捷选择：</div>
            <Space wrap>
              {[
                { label: '1个月', months: 1 },
                { label: '2个月', months: 2 },
                { label: '3个月', months: 3 },
                { label: '6个月', months: 6 },
                { label: '1年', months: 12 },
                { label: '2年', months: 24 },
                { label: '3年', months: 36 },
              ].map((item) => (
                <Button
                  key={item.label}
                  size="small"
                  onClick={() => {
                    const start = dayjs();
                    const end = dayjs().add(item.months, 'month');
                    formRef?.current?.setFieldsValue({
                      startDate: start,
                      endDate: end,
                    });
                  }}
                >
                  {item.label}
                </Button>
              ))}
            </Space>
          </div>

          <ProFormDatePicker
            name="startDate"
            label="开始日期"
            placeholder="不选则默认今天"
            extra="可选，不填写默认从今天开始"
          />
          <ProFormDatePicker
            name="endDate"
            label="结束日期"
            placeholder="不选则默认1年后"
            extra="可选，不填写默认生成到1年后（预览默认30天）"
          />
          <Alert
            message="点击「预览班次」可查看并编辑每个班次的可预约人数，或直接点击「直接生成」使用默认设置"
            type="info"
            showIcon
            style={{ marginTop: 8 }}
          />
        </ProForm>
      ) : (
        <div>
          {(() => {
            const totalSlots = previewData.reduce((acc, p) => acc + p.totalCount, 0);
            const warningSlots = previewData.reduce(
              (acc, p) => acc + p.slots.filter((s) => s.ruleValidation && s.ruleValidation.length > 0).length,
              0
            );
            return (
              <Alert
                message={
                  <span>
                    预览：共 <strong>{totalSlots}</strong> 个班次，可修改每个班次的可预约人数
                    {warningSlots > 0 && (
                      <span style={{ marginLeft: 12, color: '#fa8c16' }}>
                        （<ExclamationCircleOutlined style={{ marginRight: 4 }} />
                        {warningSlots} 个班次存在规则限制）
                      </span>
                    )}
                  </span>
                }
                type={warningSlots > 0 ? 'warning' : 'success'}
                showIcon
                style={{ marginBottom: 16 }}
              />
            );
          })()}

          {previewData.map((preview) => {
            // 按时段分组
            const groupedByPeriod: Record<string, typeof preview.slots> = {};
            preview.slots.forEach((slot) => {
              const periodName = slot.periodName || '其他';
              if (!groupedByPeriod[periodName]) {
                groupedByPeriod[periodName] = [];
              }
              groupedByPeriod[periodName].push(slot);
            });
            const periodNames = Object.keys(groupedByPeriod);

            return (
              <div key={preview.templateId} style={{ marginBottom: 16 }}>
                <div style={{ marginBottom: 8 }}>
                  <span style={{ fontWeight: 500 }}>
                    {preview.templateName} - {preview.doctorName} ({preview.departmentName})
                  </span>
                  {preview.dailyDurationHours !== undefined && (
                    <span style={{ marginLeft: 16, color: '#666', fontSize: 12 }}>
                      每日总时长：{preview.dailyDurationHours}小时
                      {preview.dailyDurationMinutes !== undefined && preview.dailyDurationMinutes > 0 && `${preview.dailyDurationMinutes}分钟`}
                    </span>
                  )}
                </div>

                {periodNames.length > 1 ? (
                  <Tabs
                    items={periodNames.map((periodName) => ({
                      key: periodName,
                      label: `${periodName} (${groupedByPeriod[periodName].length})`,
                      children: (
                        <Table
                          size="small"
                          dataSource={groupedByPeriod[periodName]}
                          rowKey={(record) => `${record.scheduleDate}-${record.startTime}-${record.endTime}`}
                          pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                          columns={[
                            { title: '日期', dataIndex: 'scheduleDate', width: 110 },
                            { title: '星期', dataIndex: 'weekdayName', width: 70 },
                            { title: '时间段', render: (_, record) => `${record.startTime} - ${record.endTime}`, width: 130 },
                            {
                              title: '可预约人数',
                              dataIndex: 'slotCapacity',
                              width: 120,
                              render: (val, record) => {
                                const key = `${record.scheduleDate}|${record.startTime}|${record.endTime}`;
                                const editedValue = editedCapacities[key];
                                return (
                                  <InputNumber
                                    size="small"
                                    min={1}
                                    max={200}
                                    value={editedValue !== undefined ? editedValue : val}
                                    onChange={(newVal) => {
                                      if (newVal !== null) {
                                        onCapacityChange(key, newVal);
                                      }
                                    }}
                                    style={{ width: 80 }}
                                  />
                                );
                              },
                            },
                            {
                              title: '规则校验',
                              width: 100,
                              render: (_, record) => {
                                const warnings = record.ruleValidation;
                                if (warnings && warnings.length > 0) {
                                  return (
                                    <Tooltip title={warnings.join('；')}>
                                      <Tag color="warning" icon={<ExclamationCircleOutlined />}>
                                        {warnings.length}项限制
                                      </Tag>
                                    </Tooltip>
                                  );
                                }
                                return (
                                  <Tag color="success" icon={<CheckCircleOutlined />}>
                                    通过
                                  </Tag>
                                );
                              },
                            },
                          ]}
                        />
                      ),
                    }))}
                  />
                ) : (
                  <Table
                    size="small"
                    dataSource={preview.slots}
                    rowKey={(record) => `${record.scheduleDate}-${record.startTime}-${record.endTime}`}
                    pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                    columns={[
                      { title: '日期', dataIndex: 'scheduleDate', width: 110 },
                      { title: '星期', dataIndex: 'weekdayName', width: 70 },
                      { title: '时间段', render: (_, record) => `${record.startTime} - ${record.endTime}`, width: 130 },
                      { title: '时段', dataIndex: 'periodName', width: 80 },
                      {
                        title: '可预约人数',
                        dataIndex: 'slotCapacity',
                        width: 120,
                        render: (val, record) => {
                          const key = `${record.scheduleDate}|${record.startTime}|${record.endTime}`;
                          const editedValue = editedCapacities[key];
                          return (
                            <InputNumber
                              size="small"
                              min={1}
                              max={200}
                              value={editedValue !== undefined ? editedValue : val}
                              onChange={(newVal) => {
                                if (newVal !== null) {
                                  onCapacityChange(key, newVal);
                                }
                              }}
                              style={{ width: 80 }}
                            />
                          );
                        },
                      },
                      {
                        title: '规则校验',
                        width: 100,
                        render: (_, record) => {
                          const warnings = record.ruleValidation;
                          if (warnings && warnings.length > 0) {
                            return (
                              <Tooltip title={warnings.join('；')}>
                                <Tag color="warning" icon={<ExclamationCircleOutlined />}>
                                  {warnings.length}项限制
                                </Tag>
                              </Tooltip>
                            );
                          }
                          return (
                            <Tag color="success" icon={<CheckCircleOutlined />}>
                              通过
                            </Tag>
                          );
                        },
                      },
                    ]}
                  />
                )}
              </div>
            );
          })}
        </div>
      )}
    </Modal>
  );
};

export default GenerateScheduleModal;
