import { Modal, App, Switch, Select, Table, InputNumber, Button, Space, Spin, Alert, Empty, Divider, Card } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useState, useEffect } from 'react';
import { consultationFeeTypeApi, consultationFeeTemplateApi, doctorConsultationFeeApi, storeApi, departmentApi } from '@hospital/api';
import type { ConsultationFeeType, ConsultationFeeTemplateWithType, StoreDepartmentFeeGroup, Store, Department, DoctorConsultationFeeItem } from '@hospital/shared';

interface DoctorConsultationFeeModalProps {
  open: boolean;
  doctorId: string;
  doctorName: string;
  onClose: () => void;
}

interface FeeConfig {
  storeId: string;
  storeName: string;
  departmentId: string;
  departmentName: string;
  fees: DoctorConsultationFeeItem[];
}

const DoctorConsultationFeeModal: React.FC<DoctorConsultationFeeModalProps> = ({
  open,
  doctorId,
  doctorName,
  onClose,
}) => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [useFeeTemplate, setUseFeeTemplate] = useState(false);
  
  // 数据
  const [feeTypes, setFeeTypes] = useState<ConsultationFeeType[]>([]);
  const [templates, setTemplates] = useState<ConsultationFeeTemplateWithType[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [feeConfigs, setFeeConfigs] = useState<FeeConfig[]>([]);
  
  // 新增配置表单
  const [selectedStoreId, setSelectedStoreId] = useState<string | undefined>();
  const [selectedDepartmentId, setSelectedDepartmentId] = useState<string | undefined>();

  useEffect(() => {
    if (open && doctorId) {
      loadData();
    }
  }, [open, doctorId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [typesRes, templatesRes, storesRes, deptsRes, settingRes] = await Promise.all([
        consultationFeeTypeApi.getList({ status: 1 }),
        consultationFeeTemplateApi.getList(),
        storeApi.getList({ pageSize: 100, status: 1 }),
        departmentApi.getList({ pageSize: 100, status: 1 }),
        doctorConsultationFeeApi.getFeeSetting(doctorId),
      ]);
      
      setFeeTypes(typesRes);
      setTemplates(templatesRes);
      setStores(storesRes.data ?? []);
      setDepartments(deptsRes.data ?? []);
      setUseFeeTemplate(settingRes.useFeeTemplate === 1);
      
      // 转换已有配置为分组格式
      const grouped = await doctorConsultationFeeApi.getFeesGrouped(doctorId);
      setFeeConfigs(grouped.map(g => ({
        storeId: g.storeId,
        storeName: g.storeName,
        departmentId: g.departmentId,
        departmentName: g.departmentName,
        fees: g.fees,
      })));
    } catch (error: any) {
      message.error(error.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUseFeeTemplateChange = async (checked: boolean) => {
    setUseFeeTemplate(checked);
    try {
      await doctorConsultationFeeApi.updateUseTemplate(doctorId, checked ? 1 : 0);
      message.success(checked ? '已启用诊费模板' : '已关闭诊费模板');
    } catch (error: any) {
      message.error(error.message || '操作失败');
      setUseFeeTemplate(!checked);
    }
  };

  const handleAddConfig = () => {
    if (!selectedStoreId || !selectedDepartmentId) {
      message.warning('请先选择门店和科室');
      return;
    }
    
    // 检查是否已存在
    const exists = feeConfigs.some(
      c => c.storeId === selectedStoreId && c.departmentId === selectedDepartmentId
    );
    if (exists) {
      message.warning('该门店-科室组合已存在配置');
      return;
    }
    
    const store = stores.find(s => s.id === selectedStoreId);
    const dept = departments.find(d => d.id === selectedDepartmentId);
    
    // 创建默认诊费配置（使用模板值或0）
    const defaultFees: DoctorConsultationFeeItem[] = feeTypes.map(ft => {
      const template = templates.find(t => t.feeTypeId === ft.id);
      return {
        feeTypeId: ft.id,
        feeTypeName: ft.name,
        feeTypeCode: ft.code,
        initialFee: template?.initialFee ?? 0,
        followUpFee: template?.followUpFee ?? 0,
      };
    });
    
    setFeeConfigs([
      ...feeConfigs,
      {
        storeId: selectedStoreId,
        storeName: store?.name || '',
        departmentId: selectedDepartmentId,
        departmentName: dept?.name || '',
        fees: defaultFees,
      },
    ]);
    
    setSelectedStoreId(undefined);
    setSelectedDepartmentId(undefined);
  };

  const handleDeleteConfig = async (index: number) => {
    const config = feeConfigs[index];
    try {
      await doctorConsultationFeeApi.deleteByStoreDepartment(
        doctorId,
        config.storeId,
        config.departmentId
      );
      const newConfigs = [...feeConfigs];
      newConfigs.splice(index, 1);
      setFeeConfigs(newConfigs);
      message.success('删除成功');
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleFeeChange = (
    configIndex: number,
    feeIndex: number,
    field: 'initialFee' | 'followUpFee',
    value: number | null
  ) => {
    const newConfigs = [...feeConfigs];
    newConfigs[configIndex].fees[feeIndex] = {
      ...newConfigs[configIndex].fees[feeIndex],
      [field]: value ?? 0,
    };
    setFeeConfigs(newConfigs);
  };

  const handleSaveConfig = async (configIndex: number) => {
    const config = feeConfigs[configIndex];
    setSaving(true);
    try {
      await doctorConsultationFeeApi.batchSave(doctorId, {
        doctorId,
        storeId: config.storeId,
        departmentId: config.departmentId,
        fees: config.fees,
      });
      message.success('保存成功');
    } catch (error: any) {
      message.error(error.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const feeColumns = [
    {
      title: '诊费类型',
      dataIndex: 'feeTypeName',
      width: 120,
    },
    {
      title: '初诊金额',
      dataIndex: 'initialFee',
      width: 150,
      render: (_: any, record: DoctorConsultationFeeItem, feeIndex: number, configIndex: number) => (
        <InputNumber
          value={record.initialFee}
          min={0}
          precision={2}
          addonAfter="元"
          style={{ width: 120 }}
          onChange={(value) => handleFeeChange(configIndex, feeIndex, 'initialFee', value)}
        />
      ),
    },
    {
      title: '复诊金额',
      dataIndex: 'followUpFee',
      width: 150,
      render: (_: any, record: DoctorConsultationFeeItem, feeIndex: number, configIndex: number) => (
        <InputNumber
          value={record.followUpFee}
          min={0}
          precision={2}
          addonAfter="元"
          style={{ width: 120 }}
          onChange={(value) => handleFeeChange(configIndex, feeIndex, 'followUpFee', value)}
        />
      ),
    },
  ];

  return (
    <Modal
      title={`诊费管理 — ${doctorName}`}
      open={open}
      onCancel={onClose}
      footer={null}
      width={800}
      destroyOnClose
    >
      <Spin spinning={loading}>
        <div style={{ marginBottom: 16 }}>
          <Space>
            <span>是否使用诊费模板：</span>
            <Switch
              checked={useFeeTemplate}
              onChange={handleUseFeeTemplateChange}
              checkedChildren="是"
              unCheckedChildren="否"
            />
          </Space>
          {useFeeTemplate && (
            <Alert
              message="已启用诊费模板，该医生所有门店都将使用全局诊费模板配置"
              type="info"
              showIcon
              style={{ marginTop: 8 }}
            />
          )}
        </div>

        {!useFeeTemplate && (
          <>
            <Divider orientation="left">自定义诊费配置</Divider>
            
            {/* 新增配置区域 */}
            <Card size="small" style={{ marginBottom: 16 }}>
              <Space wrap>
                <span>选择门店：</span>
                <Select
                  placeholder="请选择门店"
                  style={{ width: 180 }}
                  value={selectedStoreId}
                  onChange={setSelectedStoreId}
                  options={stores.map(s => ({ label: s.name, value: s.id }))}
                  allowClear
                />
                <span>选择科室：</span>
                <Select
                  placeholder="请选择科室"
                  style={{ width: 180 }}
                  value={selectedDepartmentId}
                  onChange={setSelectedDepartmentId}
                  options={departments.map(d => ({ label: d.name, value: d.id }))}
                  allowClear
                />
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleAddConfig}
                >
                  添加配置
                </Button>
              </Space>
            </Card>

            {/* 已有配置列表 */}
            {feeConfigs.length === 0 ? (
              <Empty description="暂无诊费配置，请添加" />
            ) : (
              feeConfigs.map((config, configIndex) => (
                <Card
                  key={`${config.storeId}_${config.departmentId}`}
                  size="small"
                  title={
                    <Space>
                      <span>{config.storeName}</span>
                      <span>-</span>
                      <span>{config.departmentName}</span>
                    </Space>
                  }
                  extra={
                    <Space>
                      <Button
                        type="primary"
                        size="small"
                        onClick={() => handleSaveConfig(configIndex)}
                        loading={saving}
                      >
                        保存
                      </Button>
                      <Button
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={() => handleDeleteConfig(configIndex)}
                      >
                        删除
                      </Button>
                    </Space>
                  }
                  style={{ marginBottom: 16 }}
                >
                  <Table
                    rowKey="feeTypeId"
                    columns={feeColumns.map(col => {
                      if (col.dataIndex === 'initialFee' || col.dataIndex === 'followUpFee') {
                        return {
                          ...col,
                          render: (_: any, record: DoctorConsultationFeeItem, feeIndex: number) =>
                            col.render!(_, record, feeIndex, configIndex),
                        };
                      }
                      return col;
                    })}
                    dataSource={config.fees}
                    pagination={false}
                    size="small"
                    bordered
                  />
                </Card>
              ))
            )}
          </>
        )}
      </Spin>
    </Modal>
  );
};

export default DoctorConsultationFeeModal;
