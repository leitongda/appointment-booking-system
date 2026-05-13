import React, { useMemo } from 'react';
import { useLocation } from '@umijs/max';

const PageTransitionWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const animationKey = useMemo(() => location.pathname, [location.pathname]);

  return (
    <div key={animationKey} className="page-transition-wrapper">
      {children}
    </div>
  );
};

export default PageTransitionWrapper;
