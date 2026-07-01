import type { ProColumns } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { rrwebMaskTextCell } from '@/utils/tableCellProps';

/**
 * 表格列预设（Column Presets）
 *
 * 收敛 admin 多页面（appointment/list、appointment/queue、waitlist/index、
 * medical-record/index、follow-up/records、follow-up/tasks 等）重复复制的
 * ProColumns 列定义：patientName / patientPhone / doctorName / departmentName /
 * status。
 *
 * 设计原则：
 * - 每个工厂返回一个 ProColumns 对象，默认值取各页面最常用的配置。
 * - 通过 `overrides` 参数合并各页差异（title / width / render / onCell 等），
 *   保证行为与替换前逐字一致。
 * - 合并为浅合并（对象层级用 `{...base, ...overrides}`），调用方需要整体
 *   替换嵌套对象时直接在 overrides 中传完整对象即可。
 *
 * 状态列的 STATUS_MAP 各页面字典不同（预约状态/病历状态/候补状态/随访状态），
 * 因此不内置 map，由调用方通过 `statusMap` 参数传入。
 */

// 状态映射的标准结构：{ text, color }
export type ColumnStatusMap<K extends string | number = string | number> = Record<
  K,
  { text: string; color: string }
>;

/** 合并 helper：浅合并 base 与 overrides，overrides 优先 */
function mergeColumn<T>(
  base: T,
  overrides?: Partial<T>
): T {
  return overrides ? { ...base, ...overrides } : base;
}

/**
 * 患者姓名列
 *
 * 默认：title '患者'、search: false、onCell rrwebMaskTextCell（脱敏）。
 * queue 页面无脱敏（需传 overrides: { onCell: undefined }）或保留其自定义。
 */
export function patientNameColumn<T = any>(
  overrides?: Partial<ProColumns<T>>
): ProColumns<T> {
  return mergeColumn<ProColumns<T>>(
    {
      title: '患者',
      dataIndex: 'patientName',
      search: false,
      onCell: rrwebMaskTextCell,
    },
    overrides
  );
}

/**
 * 患者手机列
 *
 * 默认：title '手机号'、search: false、onCell rrwebMaskTextCell（脱敏）。
 */
export function patientPhoneColumn<T = any>(
  overrides?: Partial<ProColumns<T>>
): ProColumns<T> {
  return mergeColumn<ProColumns<T>>(
    {
      title: '手机号',
      dataIndex: 'patientPhone',
      search: false,
      onCell: rrwebMaskTextCell,
    },
    overrides
  );
}

/**
 * 医生姓名列
 *
 * 默认：title '医生'、search: false、不脱敏。
 */
export function doctorNameColumn<T = any>(
  overrides?: Partial<ProColumns<T>>
): ProColumns<T> {
  return mergeColumn<ProColumns<T>>(
    {
      title: '医生',
      dataIndex: 'doctorName',
      search: false,
    },
    overrides
  );
}

/**
 * 科室名称列
 *
 * 默认：title '科室'、search: false、不脱敏。
 */
export function departmentNameColumn<T = any>(
  overrides?: Partial<ProColumns<T>>
): ProColumns<T> {
  return mergeColumn<ProColumns<T>>(
    {
      title: '科室',
      dataIndex: 'departmentName',
      search: false,
    },
    overrides
  );
}

/**
 * 状态列（Tag 渲染）
 *
 * 由于各页面的 STATUS_MAP 字典不同（预约/病历/候补/随访状态），map 必须由
 * 调用方传入。渲染逻辑统一为：
 *   const status = statusMap[record.status] || { text: '未知', color: 'default' };
 *   return <Tag color={status.color}>{status.text}</Tag>;
 *
 * 与各页面原渲染逐字一致（appointment/list、waitlist、medical-record、queue 均为
 * 此 fallback 形态；follow-up/tasks 略有差异，调用方通过 overrides.render 覆盖）。
 *
 * 默认不开启 search（valueEnum），需要筛选的页面通过 overrides 传 valueType/valueEnum。
 */
export function statusColumn<T = any>(
  statusMap: ColumnStatusMap,
  overrides?: Partial<ProColumns<T>>
): ProColumns<T> {
  return mergeColumn<ProColumns<T>>(
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      search: false,
      render: (_: any, record: any) => {
        const status = statusMap[record.status] || { text: '未知', color: 'default' };
        return <Tag color={status.color}>{status.text}</Tag>;
      },
    },
    overrides
  );
}
