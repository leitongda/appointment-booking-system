import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Input, List, Spin, Empty, Typography, Space, message } from 'antd';
import { SearchOutlined, EnvironmentOutlined, AimOutlined } from '@ant-design/icons';
import './index.less';

const { Text } = Typography;

export interface LocationInfo {
  longitude: string;
  latitude: string;
  province?: string;
  city?: string;
  district?: string;
  address?: string;
  formattedAddress?: string;
}

interface MapLocationPickerProps {
  value?: LocationInfo;
  onChange?: (value: LocationInfo) => void;
  defaultCenter?: [number, number];
  defaultZoom?: number;
  height?: number;
  placeholder?: string;
}

const MapLocationPicker: React.FC<MapLocationPickerProps> = ({
  value,
  onChange,
  defaultCenter = [106.619922, 26.644479], // 默认贵阳
  defaultZoom = 15,
  height = 400,
  placeholder = '搜索地址...',
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<AMap.Map | null>(null);
  const markerRef = useRef<AMap.Marker | null>(null);
  const geocoderRef = useRef<AMap.Geocoder | null>(null);
  const placeSearchRef = useRef<AMap.PlaceSearch | null>(null);

  const [searchKeyword, setSearchKeyword] = useState('');
  const [searchResults, setSearchResults] = useState<AMap.POI[]>([]);
  const [searching, setSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [currentLocation, setCurrentLocation] = useState<LocationInfo | null>(value || null);
  const [mapReady, setMapReady] = useState(false);

  // 检查 AMap 是否加载完成
  const checkAMapLoaded = useCallback(() => {
    return typeof window !== 'undefined' && (window as any).AMap;
  }, []);

  // 初始化地图
  useEffect(() => {
    let checkInterval: NodeJS.Timeout;
    let mounted = true;

    const initMap = () => {
      if (!mapContainerRef.current || !checkAMapLoaded()) return;

      const AMapLib = (window as any).AMap;

      // 创建地图
      const map = new AMapLib.Map(mapContainerRef.current, {
        zoom: defaultZoom,
        center: value?.longitude && value?.latitude 
          ? [parseFloat(value.longitude), parseFloat(value.latitude)]
          : defaultCenter,
        viewMode: '2D',
        resizeEnable: true,
      });

      mapRef.current = map;

      // 创建 Geocoder
      geocoderRef.current = new AMapLib.Geocoder({
        extensions: 'all',
      });

      // 创建 PlaceSearch
      placeSearchRef.current = new AMapLib.PlaceSearch({
        pageSize: 10,
        pageIndex: 1,
        extensions: 'all',
      });

      // 创建标记点
      const marker = new AMapLib.Marker({
        draggable: true,
        animation: 'AMAP_ANIMATION_DROP',
      });

      // 如果有初始值，设置标记点位置
      if (value?.longitude && value?.latitude) {
        marker.setPosition([parseFloat(value.longitude), parseFloat(value.latitude)]);
        marker.setMap(map);
      }

      markerRef.current = marker;

      // 标记点拖拽结束事件
      marker.on('dragend', () => {
        const pos = marker.getPosition();
        if (pos) {
          reverseGeocode([pos.getLng(), pos.getLat()]);
        }
      });

      // 地图点击事件
      map.on('click', (e: any) => {
        const lng = e.lnglat.getLng();
        const lat = e.lnglat.getLat();
        
        marker.setPosition([lng, lat]);
        marker.setMap(map);
        
        reverseGeocode([lng, lat]);
      });

      if (mounted) {
        setMapReady(true);
      }
    };

    // 轮询检查 AMap 是否加载完成
    if (checkAMapLoaded()) {
      initMap();
    } else {
      checkInterval = setInterval(() => {
        if (checkAMapLoaded()) {
          clearInterval(checkInterval);
          initMap();
        }
      }, 100);
    }

    return () => {
      mounted = false;
      if (checkInterval) clearInterval(checkInterval);
      if (mapRef.current) {
        mapRef.current.destroy();
        mapRef.current = null;
      }
    };
  }, []);

  // 逆地理编码
  const reverseGeocode = useCallback((lnglat: [number, number]) => {
    if (!geocoderRef.current) return;

    geocoderRef.current.getAddress(lnglat, (status, result) => {
      if (status === 'complete' && result.regeocode) {
        const { formattedAddress, addressComponent } = result.regeocode;
        const locationInfo: LocationInfo = {
          longitude: lnglat[0].toFixed(6),
          latitude: lnglat[1].toFixed(6),
          province: addressComponent.province,
          city: addressComponent.city || addressComponent.province, // 直辖市没有 city
          district: addressComponent.district,
          address: formattedAddress,
          formattedAddress,
        };
        
        setCurrentLocation(locationInfo);
        onChange?.(locationInfo);
      } else {
        // 如果逆地理编码失败，至少返回经纬度
        const locationInfo: LocationInfo = {
          longitude: lnglat[0].toFixed(6),
          latitude: lnglat[1].toFixed(6),
        };
        setCurrentLocation(locationInfo);
        onChange?.(locationInfo);
      }
    });
  }, [onChange]);

  // 搜索地址
  const handleSearch = useCallback((keyword: string) => {
    if (!keyword.trim() || !placeSearchRef.current) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    setSearching(true);
    setShowResults(true);

    placeSearchRef.current.search(keyword, (status, result) => {
      setSearching(false);
      if (status === 'complete' && result.poiList) {
        setSearchResults(result.poiList.pois);
      } else {
        setSearchResults([]);
      }
    });
  }, []);

  // 选择搜索结果
  const handleSelectPOI = useCallback((poi: AMap.POI) => {
    if (!mapRef.current || !markerRef.current) return;

    const lng = poi.location.getLng();
    const lat = poi.location.getLat();

    // 移动地图中心
    mapRef.current.setCenter([lng, lat]);
    mapRef.current.setZoom(17);

    // 更新标记点
    markerRef.current.setPosition([lng, lat]);
    markerRef.current.setMap(mapRef.current);

    // 设置位置信息
    const locationInfo: LocationInfo = {
      longitude: lng.toFixed(6),
      latitude: lat.toFixed(6),
      province: poi.pname,
      city: poi.cityname,
      district: poi.adname,
      address: poi.address || poi.name,
      formattedAddress: `${poi.pname}${poi.cityname}${poi.adname}${poi.address || poi.name}`,
    };

    setCurrentLocation(locationInfo);
    onChange?.(locationInfo);
    setShowResults(false);
    setSearchKeyword(poi.name);
  }, [onChange]);

  // 防抖搜索
  const searchTimeoutRef = useRef<NodeJS.Timeout>();
  const handleSearchInput = useCallback((value: string) => {
    setSearchKeyword(value);
    
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    searchTimeoutRef.current = setTimeout(() => {
      handleSearch(value);
    }, 300);
  }, [handleSearch]);

  // 定位到当前位置
  const handleLocate = useCallback(() => {
    if (!mapRef.current) {
      message.warning('地图未加载完成');
      return;
    }

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { longitude, latitude } = position.coords;
          mapRef.current?.setCenter([longitude, latitude]);
          mapRef.current?.setZoom(17);
          
          if (markerRef.current) {
            markerRef.current.setPosition([longitude, latitude]);
            markerRef.current.setMap(mapRef.current!);
          }
          
          reverseGeocode([longitude, latitude]);
        },
        () => {
          message.error('无法获取当前位置');
        }
      );
    } else {
      message.error('浏览器不支持定位');
    }
  }, [reverseGeocode]);

  return (
    <div className="map-location-picker">
      {/* 搜索框 */}
      <div className="map-search-container">
        <Input
          placeholder={placeholder}
          prefix={<SearchOutlined />}
          suffix={
            <AimOutlined 
              className="locate-btn" 
              onClick={handleLocate}
              title="定位当前位置"
            />
          }
          value={searchKeyword}
          onChange={(e) => handleSearchInput(e.target.value)}
          onFocus={() => searchResults.length > 0 && setShowResults(true)}
          allowClear
        />
        
        {/* 搜索结果列表 */}
        {showResults && (
          <div className="search-results">
            {searching ? (
              <div className="search-loading">
                <Spin size="small" />
                <span>搜索中...</span>
              </div>
            ) : searchResults.length > 0 ? (
              <List
                size="small"
                dataSource={searchResults}
                renderItem={(item) => (
                  <List.Item 
                    className="search-result-item"
                    onClick={() => handleSelectPOI(item)}
                  >
                    <Space>
                      <EnvironmentOutlined />
                      <div>
                        <div className="poi-name">{item.name}</div>
                        <Text type="secondary" className="poi-address">
                          {item.pname}{item.cityname}{item.adname}{item.address}
                        </Text>
                      </div>
                    </Space>
                  </List.Item>
                )}
              />
            ) : searchKeyword ? (
              <Empty description="未找到相关地址" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : null}
          </div>
        )}
      </div>

      {/* 地图容器 */}
      <div 
        ref={mapContainerRef} 
        className="map-container"
        style={{ height }}
        onClick={() => setShowResults(false)}
      >
        {!mapReady && (
          <div className="map-loading">
            <Spin tip="地图加载中..."><span /></Spin>
          </div>
        )}
      </div>

      {/* 当前选择信息 */}
      {currentLocation && (
        <div className="location-info">
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <div>
              <EnvironmentOutlined style={{ marginRight: 8, color: '#1890ff' }} />
              <Text strong>当前选择：</Text>
              <Text>{currentLocation.formattedAddress || currentLocation.address || '未知地址'}</Text>
            </div>
            <div style={{ marginLeft: 22 }}>
              <Text type="secondary">
                经度: {currentLocation.longitude} | 纬度: {currentLocation.latitude}
              </Text>
            </div>
          </Space>
        </div>
      )}
    </div>
  );
};

export default MapLocationPicker;

