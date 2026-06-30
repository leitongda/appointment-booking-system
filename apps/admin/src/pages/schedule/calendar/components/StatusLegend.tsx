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
      <span style={{ margin: '0 8px', color: 'var(--color-border)' }}>|</span>
      <div className="legend-item" role="listitem" aria-label="草稿：灰色圆点表示排班未发布">
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-border)', display: 'inline-block' }} />
        <span>草稿</span>
      </div>
      <div className="legend-item" role="listitem" aria-label="已发布：绿色圆点表示排班已发布">
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-success)', display: 'inline-block' }} />
        <span>已发布</span>
      </div>
      <div className="legend-item" role="listitem" aria-label="已撤回：红色圆点表示排班已撤回">
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-error)', display: 'inline-block' }} />
        <span>已撤回</span>
      </div>
    </div>
  );
};

export default StatusLegend;

