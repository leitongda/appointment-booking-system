/** 业务物料组件定义 — 医疗 SaaS 场景专用组件 */

import type { MaterialComponent } from '@hospital/shared';

export const businessMaterials: MaterialComponent[] = [
  // -------------------------------------------------------------------------
  // BizAppointmentCard — 预约卡片
  // -------------------------------------------------------------------------
  {
    componentName: 'BizAppointmentCard',
    title: '预约卡片',
    icon: 'CreditCardOutlined',
    category: 'business',
    defaultProps: {
      doctorName: '张医生',
      departmentName: '内科',
      appointmentTime: '2026-06-10 09:00',
      status: 'pending',
      statusText: '待就诊',
      avatar: '',
    },
    configureSchema: [
      { key: 'doctorName', label: '医生姓名', type: 'input', defaultValue: '张医生' },
      { key: 'departmentName', label: '科室名称', type: 'input', defaultValue: '内科' },
      { key: 'appointmentTime', label: '预约时间', type: 'input', defaultValue: '2026-06-10 09:00' },
      {
        key: 'status',
        label: '预约状态',
        type: 'select',
        defaultValue: 'pending',
        options: [
          { label: '待就诊', value: 'pending' },
          { label: '已确认', value: 'confirmed' },
          { label: '已完成', value: 'completed' },
          { label: '已取消', value: 'cancelled' },
          { label: '已爽约', value: 'missed' },
        ],
      },
      { key: 'statusText', label: '状态文字', type: 'input', defaultValue: '待就诊' },
      { key: 'avatar', label: '医生头像 URL', type: 'image', defaultValue: '' },
    ],
  },

  // -------------------------------------------------------------------------
  // BizDoctorCard — 医生信息卡片
  // -------------------------------------------------------------------------
  {
    componentName: 'BizDoctorCard',
    title: '医生卡片',
    icon: 'CreditCardOutlined',
    category: 'business',
    defaultProps: {
      doctorName: '张医生',
      departmentName: '内科',
      title: '主任医师',
      avatar: '',
      description: '擅长内科常见病、多发病的诊治',
      consultationFee: '50',
    },
    configureSchema: [
      { key: 'doctorName', label: '医生姓名', type: 'input', defaultValue: '张医生' },
      { key: 'departmentName', label: '科室名称', type: 'input', defaultValue: '内科' },
      { key: 'title', label: '职称', type: 'input', defaultValue: '主任医师' },
      { key: 'avatar', label: '头像 URL', type: 'image', defaultValue: '' },
      { key: 'description', label: '简介', type: 'textarea', defaultValue: '擅长内科常见病、多发病的诊治' },
      { key: 'consultationFee', label: '挂号费 (元)', type: 'input', defaultValue: '50' },
    ],
  },

  // -------------------------------------------------------------------------
  // BizDepartmentPicker — 科室选择器
  // -------------------------------------------------------------------------
  {
    componentName: 'BizDepartmentPicker',
    title: '科室选择器',
    icon: 'DownSquareOutlined',
    category: 'business',
    defaultProps: {
      label: '选择科室',
      placeholder: '请选择科室',
      required: false,
      disabled: false,
    },
    configureSchema: [
      { key: 'label', label: '标签文字', type: 'input', defaultValue: '选择科室' },
      { key: 'placeholder', label: '占位文字', type: 'input', defaultValue: '请选择科室' },
      { key: 'required', label: '必填', type: 'switch', defaultValue: false },
      { key: 'disabled', label: '禁用', type: 'switch', defaultValue: false },
    ],
  },

  // -------------------------------------------------------------------------
  // BizTimeSlotPicker — 时间段选择器
  // -------------------------------------------------------------------------
  {
    componentName: 'BizTimeSlotPicker',
    title: '时间段选择器',
    icon: 'DownSquareOutlined',
    category: 'business',
    defaultProps: {
      label: '选择时间段',
      placeholder: '请选择时间段',
      required: false,
      disabled: false,
      date: '',
    },
    configureSchema: [
      { key: 'label', label: '标签文字', type: 'input', defaultValue: '选择时间段' },
      { key: 'placeholder', label: '占位文字', type: 'input', defaultValue: '请选择时间段' },
      { key: 'required', label: '必填', type: 'switch', defaultValue: false },
      { key: 'disabled', label: '禁用', type: 'switch', defaultValue: false },
      { key: 'date', label: '日期 (YYYY-MM-DD)', type: 'input', defaultValue: '' },
    ],
  },
];
