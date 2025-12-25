const StatusLegend: React.FC = () => {
  return (
    <div className="status-legend">
      <div className="legend-item">
        <span className="legend-dot available" />
        <span>可预约</span>
      </div>
      <div className="legend-item">
        <span className="legend-dot booked" />
        <span>已预约</span>
      </div>
      <div className="legend-item">
        <span className="legend-dot full" />
        <span>已满</span>
      </div>
      <div className="legend-item">
        <span className="legend-dot suspended" />
        <span>停诊</span>
      </div>
    </div>
  );
};

export default StatusLegend;

