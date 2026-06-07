import React, { useEffect, useRef, useState, useCallback } from 'react';
import { AutoComplete, Input, Spin, Alert, Tag, Tooltip, Typography, message, Space, Empty } from 'antd';
import { EnvironmentOutlined, SearchOutlined, AimOutlined, CloseCircleOutlined, HistoryOutlined, DeleteOutlined } from '@ant-design/icons';

import { amapApi } from '@hospital/api';
import type { LocationInfo } from './types';

export type { LocationInfo } from './types';
export { formatFullAddress, locationToFields, isEmptyLocation } from './types';

interface PoiOption {
  value: string;
  label: React.ReactNode;
  poi: {
    name: string;
    address: string;
    location: string;
    pname: string;
    cityname: string;
    adname: string;
  };
}

interface MapLocationPickerProps {
  value?: LocationInfo;
  onChange?: (value: LocationInfo) => void;
  placeholder?: string;
  /** 地图高度，默认 360 */
  mapHeight?: number;
  /** 初始中心点（默认贵阳） */
  defaultCenter?: [number, number];
  /** 初始缩放级别 */
  defaultZoom?: number;
}

const DEFAULT_CENTER: [number, number] = [106.713478, 26.578343];
const DEFAULT_ZOOM = 12;
const SEARCH_DEBOUNCE_MS = 300;
const HISTORY_KEY = 'amap_search_history';
const MAX_HISTORY = 10;

// --- 搜索历史 ---
interface HistoryItem {
  name: string;
  address: string;
  province: string;
  city: string;
  district: string;
  longitude: number | string;
  latitude: number | string;
  timestamp: number;
}

function loadHistory(): HistoryItem[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveToHistory(location: LocationInfo): HistoryItem[] {
  try {
    const item: HistoryItem = {
      name: location.address || [location.province, location.city, location.district].filter(Boolean).join(''),
      address: location.address,
      province: location.province,
      city: location.city,
      district: location.district,
      longitude: location.longitude,
      latitude: location.latitude,
      timestamp: Date.now(),
    };
    const history = loadHistory().filter((h) => h.name !== item.name);
    history.unshift(item);
    const updated = history.slice(0, MAX_HISTORY);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
    return updated;
  } catch {
    return [];
  }
}

function clearHistory(): void {
  try {
    localStorage.removeItem(HISTORY_KEY);
  } catch {}
}

/** 高亮文本中的关键词 */
function highlightKeyword(text: string, keyword: string): React.ReactNode {
  if (!keyword.trim() || !text) return text;
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  const parts = text.split(regex);
  // split 结果中偶数索引为非匹配片段，奇数索引为匹配片段
  return parts.map((part, i) =>
    i % 2 === 1 ? <mark key={i} style={{ background: '#ffd666', padding: 0, borderRadius: 2 }}>{part}</mark> : part
  );
}

/** 从后端代理查询 POI */
async function searchPoi(keyword: string, city?: string): Promise<PoiOption[]> {
  if (!keyword.trim()) return [];

  try {
    const result = await amapApi.searchPoi(keyword, city);
    const pois = result?.pois || [];
    return pois.map((poi) => ({
      value: poi.name,
      label: (
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>{highlightKeyword(poi.name, keyword)}</span>
          <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>{poi.adname}{poi.address}</span>
        </div>
      ),
      poi,
    }));
  } catch {
    return [];
  }
}

/** 从后端代理逆地理编码 */
async function reverseGeocode(lng: number, lat: number): Promise<LocationInfo | null> {
  try {
    const regeo = await amapApi.reverseGeocode(`${lng},${lat}`);
    if (!regeo) return null;

    const comp = regeo.addressComponent || {};
    return {
      address: regeo.formatted_address || '',
      province: comp.province || '',
      city: typeof comp.city === 'string' ? comp.city : (comp.province || ''),
      district: comp.district || '',
      longitude: lng,
      latitude: lat,
    };
  } catch {
    return null;
  }
}

const MapLocationPicker: React.FC<MapLocationPickerProps> = ({
  value,
  onChange,
  placeholder = '搜索地址（如：贵阳市观山湖区）',
  mapHeight = 360,
  defaultCenter = DEFAULT_CENTER,
  defaultZoom = DEFAULT_ZOOM,
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<AMap.Map | null>(null);
  const markerRef = useRef<AMap.Marker | null>(null);
  const [searchValue, setSearchValue] = useState('');
  const [options, setOptions] = useState<PoiOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState(false);
  const [locating, setLocating] = useState(false);
  const [searched, setSearched] = useState(false);
  const [focused, setFocused] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const initializingRef = useRef(false);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 初始化地图
  useEffect(() => {
    if (!mapRef.current || initializingRef.current) return;
    if (typeof AMap === 'undefined') {
      console.warn('AMap JS SDK 未加载，请检查 headScripts 配置');
      setMapError(true);
      return;
    }
    initializingRef.current = true;

    const center: [number, number] = value?.longitude && value?.latitude
      ? [Number(value.longitude), Number(value.latitude)]
      : defaultCenter;

    const map = new AMap.Map(mapRef.current, {
      zoom: defaultZoom,
      center,
      viewMode: '2D',
      resizeEnable: true,
    });

    // 添加缩放控件
    (AMap as any).plugin(['AMap.ToolBar', 'AMap.Scale'], () => {
      (map as any).addControl(new (AMap as any).ToolBar({ position: 'RT' }));
      (map as any).addControl(new (AMap as any).Scale({ position: 'LB' }));
    });

    const marker = new AMap.Marker({
      position: center,
      draggable: true,
    });

    map.add(marker);

    // 点击地图放置标记
    map.on('click', async (e: any) => {
      const lnglat = e.lnglat;
      marker.setPosition(lnglat);
      const info = await reverseGeocode(lnglat.getLng(), lnglat.getLat());
      if (info) {
        onChange?.(info);
      }
    });

    // 拖拽标记结束，逆地理编码
    marker.on('dragend', async () => {
      const pos = marker.getPosition();
      const info = await reverseGeocode(pos.getLng(), pos.getLat());
      if (info) {
        onChange?.(info);
      }
    });

    mapInstanceRef.current = map;
    markerRef.current = marker;
    setMapReady(true);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
      map.destroy();
      mapInstanceRef.current = null;
      markerRef.current = null;
      initializingRef.current = false;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 外部 value 变化时同步标记位置
  useEffect(() => {
    if (!markerRef.current || !mapInstanceRef.current) return;
    if (value?.longitude && value?.latitude) {
      const lnglat = new AMap.LngLat(Number(value.longitude), Number(value.latitude));
      markerRef.current.setPosition(lnglat);
      mapInstanceRef.current.setCenter(lnglat);
    }
  }, [value?.longitude, value?.latitude]);

  // POI 搜索（带防抖）
  const handleSearch = useCallback((text: string) => {
    setSearchValue(text);
    if (!text.trim()) {
      setOptions([]);
      setLoading(false);
      setSearched(false);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
      return;
    }

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    setLoading(true);
    setSearched(false);
    debounceTimerRef.current = setTimeout(async () => {
      const results = await searchPoi(text);
      setOptions(results);
      setLoading(false);
      setSearched(true);
      debounceTimerRef.current = null;
    }, SEARCH_DEBOUNCE_MS);
  }, []);

  // 定位当前位置
  const handleLocate = useCallback(async () => {
    if (!navigator.geolocation) {
      message.warning('当前浏览器不支持地理定位');
      return;
    }
    setLocating(true);
    try {
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 60000,
        });
      });
      const { longitude: lng, latitude: lat } = position.coords;
      const info = await reverseGeocode(lng, lat);
      if (info) {
        onChange?.(info);
        setHistory(saveToHistory(info));
        if (mapInstanceRef.current && markerRef.current) {
          const lnglat = new AMap.LngLat(lng, lat);
          markerRef.current.setPosition(lnglat);
          mapInstanceRef.current.setCenter(lnglat);
          mapInstanceRef.current.setZoom(16);
        }
      } else {
        message.info('定位成功但未能获取地址信息');
      }
    } catch (err: any) {
      if (err.code === 1) {
        message.warning('定位权限被拒绝，请在浏览器设置中允许定位');
      } else if (err.code === 2) {
        message.warning('无法获取位置信息，请检查网络');
      } else if (err.code === 3) {
        message.warning('定位超时，请重试');
      } else {
        message.warning('定位失败，请重试');
      }
    } finally {
      setLocating(false);
    }
  }, [onChange]);

  // 清除已选位置
  const handleClear = useCallback(() => {
    onChange?.({ address: '', province: '', city: '', district: '', longitude: 0, latitude: 0 });
    setSearchValue('');
    setOptions([]);
    if (mapInstanceRef.current && markerRef.current) {
      const center = new AMap.LngLat(defaultCenter[0], defaultCenter[1]);
      markerRef.current.setPosition(center);
      mapInstanceRef.current.setCenter(center);
      mapInstanceRef.current.setZoom(defaultZoom);
    }
  }, [onChange, defaultCenter, defaultZoom]);

  // 构建历史记录选项
  const historyOptions: PoiOption[] = focused && !searchValue.trim() && history.length > 0
    ? history.map((item) => ({
        value: item.name,
        label: (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space size={4}>
              <HistoryOutlined style={{ color: '#bbb', fontSize: 12 }} />
              <span>{item.name}</span>
            </Space>
            <span style={{ color: '#999', fontSize: 12 }}>{item.district}{item.address}</span>
          </div>
        ),
        poi: {
          name: item.name,
          address: item.address,
          location: `${item.longitude},${item.latitude}`,
          pname: item.province,
          cityname: item.city,
          adname: item.district,
        },
      }))
    : [];

  // 合并选项：输入时显示搜索结果，未输入时显示历史
  const displayOptions = searchValue.trim() ? options : historyOptions;

  // 选择 POI
  const handleSelect = useCallback(async (_value: string, option: any) => {
    const poi = option.poi;
    if (!poi?.location) return;

    const [lng, lat] = poi.location.split(',').map(Number);
    if (mapInstanceRef.current && markerRef.current) {
      const lnglat = new AMap.LngLat(lng, lat);
      markerRef.current.setPosition(lnglat);
      mapInstanceRef.current.setCenter(lnglat);
      mapInstanceRef.current.setZoom(16);
    }

    // 使用 POI 自带信息组装 LocationInfo
    const info: LocationInfo = {
      address: poi.address || poi.name,
      province: poi.pname || '',
      city: poi.cityname || '',
      district: poi.adname || '',
      longitude: lng,
      latitude: lat,
    };
    onChange?.(info);
    setSearchValue(poi.name);
    setOptions([]);
    setHistory(saveToHistory(info));
  }, [onChange]);

  // 输入框聚焦时加载历史
  const handleFocus = useCallback(() => {
    setFocused(true);
    setHistory(loadHistory());
  }, []);

  // 清除搜索历史
  const handleClearHistory = useCallback(() => {
    clearHistory();
    setHistory([]);
  }, []);

  return (
    <div className="map-location-picker">
      <AutoComplete
        value={searchValue || value?.address || ''}
        options={displayOptions}
        onSearch={handleSearch}
        onSelect={handleSelect}
        onChange={setSearchValue}
        style={{ width: '100%', marginBottom: 8 }}
        popupMatchSelectWidth
        notFoundContent={
          searched && !loading ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="未找到相关地点，请尝试其他关键词" style={{ padding: '12px 0' }} />
          ) : focused && !searchValue.trim() && history.length === 0 ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无搜索历史" style={{ padding: '12px 0' }} />
          ) : undefined
        }
        dropdownRender={(menu) => (
          <>
            {focused && !searchValue.trim() && history.length > 0 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 8px', borderBottom: '1px solid #f0f0f0' }}>
                <span style={{ fontSize: 12, color: '#999' }}>搜索历史</span>
                <Typography.Link style={{ fontSize: 12 }} onClick={handleClearHistory}>
                  <DeleteOutlined /> 清除
                </Typography.Link>
              </div>
            )}
            {menu}
          </>
        )}
      >
        <Input
          placeholder={placeholder}
          prefix={<SearchOutlined />}
          allowClear
          onFocus={handleFocus}
          onBlur={() => setTimeout(() => setFocused(false), 200)}
          suffix={
            loading ? <Spin size="small" /> : (
              <Tooltip title="定位到当前位置">
                <AimOutlined
                  style={{ color: locating ? '#1890ff' : '#bbb', cursor: 'pointer', fontSize: 14 }}
                  spin={locating}
                  onClick={handleLocate}
                />
              </Tooltip>
            )
          }
        />
      </AutoComplete>

      <div
        ref={mapRef}
        style={{
          width: '100%',
          height: mapHeight,
          borderRadius: 6,
          border: '1px solid #d9d9d9',
          position: 'relative',
        }}
      >
        {mapError && (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#fafafa',
            borderRadius: 6,
            padding: 16,
          }}>
            <Alert
              type="warning"
              message="地图加载失败"
              description="高德地图 SDK 未加载，请检查 AMAP_KEY 配置或网络连接。地址搜索功能仍可使用。"
              showIcon
            />
          </div>
        )}
        {!mapReady && !mapError && (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#fafafa',
            borderRadius: 6,
          }}>
            <Spin tip="地图加载中..." />
          </div>
        )}
      </div>

      {value?.address && (
        <div style={{ marginTop: 8, fontSize: 12, color: '#666', display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4 }}>
          <EnvironmentOutlined style={{ color: '#1890ff' }} />
          {value.province && <Tag style={{ marginInlineEnd: 0 }}>{value.province}</Tag>}
          {value.city && value.city !== value.province && <Tag style={{ marginInlineEnd: 0 }}>{value.city}</Tag>}
          {value.district && <Tag style={{ marginInlineEnd: 0 }}>{value.district}</Tag>}
          <span>{value.address}</span>
          {value.longitude && value.latitude && (
            <Typography.Text
              type="secondary"
              copyable={{ text: `${value.longitude},${value.latitude}` }}
              style={{ fontSize: 12, marginLeft: 4 }}
            >
              ({value.longitude}, {value.latitude})
            </Typography.Text>
          )}
          <Tooltip title="清除位置">
            <CloseCircleOutlined
              style={{ color: '#999', cursor: 'pointer', marginLeft: 'auto' }}
              onClick={handleClear}
            />
          </Tooltip>
        </div>
      )}
    </div>
  );
};

export default MapLocationPicker;
