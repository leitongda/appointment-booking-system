/**
 * heatmap.js 类型声明
 *
 * heatmap.js v2 是纯渲染库（无官方 @types），这里给出最小可用类型。
 * 仅覆盖 h337.create 的常用配置项与实例 API。
 */
declare module 'heatmap.js' {
  export interface HeatmapDataPoint {
    x: number;
    y: number;
    value?: number;
  }

  export interface HeatmapData {
    max?: number;
    min?: number;
    data: HeatmapDataPoint[];
  }

  export interface HeatmapConfig {
    /** 渲染容器（canvas 会挂到其内部） */
    container: HTMLElement;
    /** 半径（像素） */
    radius?: number;
    /** 最大透明度 0~1 */
    maxOpacity?: number;
    /** 最小透明度 0~1 */
    minOpacity?: number;
    /** 模糊度 0~1 */
    blur?: number;
    /** 透明渐变模式，"value" 按值渐变 / "alternative" 反向 */
    opacityMode?: 'value' | 'alternative';
    /** 渐变色 [stop, color][] */
    gradient?: Record<number, string>;
    /** 自定义背景色 */
    backgroundColor?: string;
    /** 渲染宽高（默认取容器尺寸） */
    width?: number;
    height?: number;
    /** 是否使用 alpha 通道 */
    useGradientOpacity?: boolean;
    /** x 轴/Y 轴插值精度，1~10 */
    xField?: string;
    yField?: string;
    valueField?: string;
  }

  export interface HeatmapInstance {
    /** 设置/替换数据 */
    setData(data: HeatmapData): void;
    /** 在 max 未知时设置极值 */
    setDataMax(max: number): void;
    setDataMin(min: number): void;
    /** 增量添加单个点 */
    addData(point: HeatmapDataPoint): void;
    /** 移除单个点（按坐标） */
    removeData(): void;
    /** 在 (x, y) 取值 */
    getValueAt(point: { x: number; y: number }): number;
    /** 重绘 */
    repaint(): void;
    /** 销毁实例，回收 DOM */
    destroy(): void;
    /** 临时隐藏/显示 */
    hide(): void;
    show(): void;
    /** 容器节点引用 */
    _renderer?: unknown;
  }

  const h337: {
    create(config: HeatmapConfig): HeatmapInstance;
    register(pluginName: string, plugin: unknown): void;
  };

  export default h337;
}
