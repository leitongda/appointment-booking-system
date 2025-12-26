import React from 'react';
import { motion } from 'framer-motion';
import { fadeIn, viewportOptions } from './animations';

export interface SectionLabelProps {
  children: React.ReactNode;
  showDot?: boolean;
  animated?: boolean;
  className?: string;
}

/**
 * SectionLabel - A pill badge with optional pulsing dot indicator
 * Used at the start of each major section following the design system
 * 
 * Features:
 * - Rounded pill shape with accent border and tinted background
 * - Small colored dot (optionally animated/pulsing)
 * - Uppercase monospace text with wide letter-spacing
 */
export const SectionLabel: React.FC<SectionLabelProps> = ({
  children,
  showDot = true,
  animated = true,
  className = '',
}) => {
  return (
    <motion.div
      className={`
        inline-flex items-center gap-3 
        rounded-full 
        border border-accent/30 
        bg-accent/5 
        px-5 py-2
        ${className}
      `}
      variants={animated ? fadeIn : undefined}
      initial={animated ? 'hidden' : undefined}
      whileInView={animated ? 'visible' : undefined}
      viewport={animated ? viewportOptions : undefined}
    >
      {showDot && (
        <motion.span
          className="h-2 w-2 rounded-full bg-accent"
          animate={animated ? {
            scale: [1, 1.3, 1],
            opacity: [1, 0.7, 1],
          } : undefined}
          transition={animated ? {
            duration: 2,
            ease: 'easeInOut',
            repeat: Infinity,
          } : undefined}
        />
      )}
      <span className="font-mono text-xs uppercase tracking-[0.15em] text-accent">
        {children}
      </span>
    </motion.div>
  );
};

export default SectionLabel;
