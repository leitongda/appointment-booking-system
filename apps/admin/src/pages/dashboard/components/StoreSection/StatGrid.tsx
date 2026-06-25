import React from 'react';
import './index.less';

export interface StoreStatItem {
  key: string;
  title: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  suffix?: React.ReactNode;
  tone?: 'blue' | 'green' | 'purple' | 'orange' | 'red' | 'cyan';
}

interface StatGridProps {
  items: StoreStatItem[];
}

const StatGrid: React.FC<StatGridProps> = ({ items }) => {
  return (
    <div className="store-stat-grid">
      {items.map((item) => (
        <div className={`store-stat-item store-stat-item-${item.tone || 'blue'}`} key={item.key}>
          <div className="store-stat-icon">{item.icon}</div>
          <div className="store-stat-content">
            <div className="store-stat-title">{item.title}</div>
            <div className="store-stat-value">
              <span>{item.value}</span>
              {item.suffix ? <span className="store-stat-suffix">{item.suffix}</span> : null}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default StatGrid;
