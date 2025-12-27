import { Avatar, Select, Space, Spin } from 'antd';
import { UserOutlined } from '@ant-design/icons';
import { useState, useEffect } from 'react';
import { doctorApi, departmentApi } from '@hospital/api';
import type { Doctor, Department } from '@hospital/shared';

interface DoctorSelectorProps {
  selectedDoctor: Doctor | null;
  onSelect: (doctor: Doctor | null) => void;
}

const DoctorSelector: React.FC<DoctorSelectorProps> = ({ selectedDoctor, onSelect }) => {
  const [loading, setLoading] = useState(false);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [selectedDeptId, setSelectedDeptId] = useState<string>();

  useEffect(() => {
    loadDepartments();
  }, []);

  useEffect(() => {
    if (selectedDeptId) {
      loadDoctors(selectedDeptId);
    } else {
      setDoctors([]);
    }
  }, [selectedDeptId]);

  const loadDepartments = async () => {
    try {
      const res = await departmentApi.getList({ pageSize: 100, status: 1 });
      const deptList = res.data ?? [];
      setDepartments(deptList);
      // 默认选择第一个科室
      if (deptList.length === 1 && !selectedDeptId) {
        setSelectedDeptId(deptList[0].id);
      }
    } catch (error) {
      console.error('加载科室失败', error);
    }
  };

  const loadDoctors = async (deptId: string) => {
    setLoading(true);
    try {
      const data = await doctorApi.getByDepartment(deptId);
      const doctorList = data ?? [];
      setDoctors(doctorList);
      // 默认选择第一个医生
      if (doctorList.length === 1 && !selectedDoctor) {
        onSelect(doctorList[0]);
      }
    } catch (error) {
      console.error('加载医生失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeptChange = (deptId: string) => {
    setSelectedDeptId(deptId);
    onSelect(null);
  };

  const handleDoctorChange = (doctorId: string) => {
    const doctor = doctors.find(d => d.id === doctorId);
    onSelect(doctor || null);
  };

  // 清除选择
  const handleClear = () => {
    onSelect(null);
    setSelectedDeptId(undefined);
    setDoctors([]);
  };

  return (
    <div className="doctor-selector">
      {selectedDoctor ? (
        <div className="doctor-info">
          <Avatar 
            src={selectedDoctor.avatar} 
            size={64} 
            icon={<UserOutlined />}
            className="doctor-avatar"
          />
          <div className="doctor-details">
            <div className="doctor-name">{selectedDoctor.name}</div>
            <div className="doctor-meta">
              <Space split="|">
                <span>{selectedDoctor.departmentName || '-'}</span>
                <span>{selectedDoctor.title || '-'}</span>
              </Space>
            </div>
          </div>
          <a onClick={handleClear} style={{ marginLeft: 16, color: '#1890ff' }}>
            重新选择
          </a>
        </div>
      ) : (
        <Space size="middle">
          <Select
            style={{ width: 200 }}
            placeholder="选择科室"
            showSearch
            optionFilterProp="label"
            value={selectedDeptId}
            onChange={handleDeptChange}
            options={departments.map(d => ({ label: d.name, value: d.id }))}
          />
          <Spin spinning={loading}>
            <Select
              style={{ width: 200 }}
              placeholder="选择医生"
              showSearch
              optionFilterProp="label"
              disabled={!selectedDeptId}
              value={selectedDoctor?.id}
              onChange={handleDoctorChange}
              options={doctors.map(d => ({ 
                label: `${d.name} - ${d.title || ''}`, 
                value: d.id 
              }))}
            />
          </Spin>
        </Space>
      )}
    </div>
  );
};

export default DoctorSelector;

