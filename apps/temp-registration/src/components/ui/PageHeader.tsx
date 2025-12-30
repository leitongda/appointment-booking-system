import React from 'react';
import { motion } from 'framer-motion';
import { history } from 'umi';

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  showBack?: boolean;
  onBack?: () => void;
  rightAction?: React.ReactNode;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  showBack = true,
  onBack,
  rightAction,
  className = '',
}) => {
  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      history.back();
    }
  };

  return (
    <motion.header
      className={`
        sticky top-0 z-50 
        bg-gradient-to-r from-primary to-accent
        px-4 py-4 safe-area-top
        ${className}
      `}
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {showBack && (
            <button
              onClick={handleBack}
              className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center 
                         text-white active:bg-white/30 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          )}
          <div>
            <h1 className="text-xl font-semibold text-white">{title}</h1>
            {subtitle && (
              <p className="text-sm text-white/80 mt-0.5">{subtitle}</p>
            )}
          </div>
        </div>
        {rightAction && (
          <div className="text-white">{rightAction}</div>
        )}
      </div>
    </motion.header>
  );
};

export default PageHeader;


