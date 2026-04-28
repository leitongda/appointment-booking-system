const StatusLegend: React.FC = () => {
  return (
    <div className="status-legend" role="list" aria-label="排班状态图例">
      <div className="legend-item" role="listitem" aria-label="可预约：绿色圆点表示该时段有剩余号源">
        <span className="legend-dot available" aria-hidden="true" />
        <span>可预约</span>
      </div>
      <div className="legend-item" role="listitem" aria-label="已预约：蓝色圆点表示该时段已有患者预约">
        <span className="legend-dot booked" aria-hidden="true" />
        <span>已预约</span>
      </div>
      <div className="legend-item" role="listitem" aria-label="已满：红色圆点表示该时段号源已全部约满">
        <span className="legend-dot full" aria-hidden="true" />
        <span>已满</span>
      </div>
      <div className="legend-item" role="listitem" aria-label="停诊：灰色圆点表示该时段已停诊">
        <span className="legend-dot suspended" aria-hidden="true" />
        <span>停诊</span>
      </div>
      <div className="legend-item" role="listitem" aria-label="被覆盖：灰色圆点表示该时段已被自定义排班覆盖">
        <span className="legend-dot overridden" aria-hidden="true" />
        <span>被覆盖</span>
      </div>
    </div>
  );
};

export default StatusLegend;

