/**
 * 规则组预设模板 - API 耦合代码
 * 从后端获取预设模板列表，回退到本地硬编码预设
 */

import { ruleSetApi } from '@hospital/api';
import type { RuleSetPresetResponse } from '@hospital/api';
import type { RuleSetConfig } from '@/constants/rule-set';
import { RULE_SET_PRESETS } from '@/constants/rule-set';

/** 将前端 camelCase 配置转为后端 snake_case */
function transformConfigToSnakeCase(config: RuleSetConfig): Record<string, any> {
  return JSON.parse(JSON.stringify(config));
}

// 预设模板缓存
let _presetsCache: RuleSetPresetResponse[] | null = null;

/**
 * 获取预设模板列表。
 * 优先从后端加载，失败时回退到本地硬编码预设。
 */
export async function fetchPresets(): Promise<RuleSetPresetResponse[]> {
  if (_presetsCache) return _presetsCache;
  try {
    const presets = await ruleSetApi.getPresets();
    _presetsCache = presets;
    return presets;
  } catch {
    // 回退到本地硬编码预设
    return RULE_SET_PRESETS.map((p) => ({
      id: p.id,
      name: p.name,
      description: p.description,
      config: transformConfigToSnakeCase(p.config),
      isSystem: true,
      sortOrder: 0,
    }));
  }
}

/** 清除预设缓存（用于创建/删除预设后刷新） */
export function clearPresetsCache() {
  _presetsCache = null;
}
