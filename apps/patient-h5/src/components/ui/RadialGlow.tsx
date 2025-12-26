import React from 'react';
import { motion } from 'framer-motion';

export interface RadialGlowProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  color?: 'accent' | 'secondary' | 'custom';
  customColor?: string;
  opacity?: number;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'center';
  animated?: boolean;
  className?: string;
}

/**
 * RadialGlow - A decorative radial gradient glow element
 * 
 * Used for atmospheric depth and ambient warmth in sections
 * Positioned at corners or center of containers
 */
export const RadialGlow: React.FC<RadialGlowProps> = ({
  size = 'lg',
  color = 'accent',
  customColor,
  opacity = 0.06,
  position = 'top-right',
  animated = false,
  className = '',
}) => {
  const sizeClasses = {
    sm: 'w-32 h-32',
    md: 'w-48 h-48',
    lg: 'w-64 h-64',
    xl: 'w-96 h-96',
  };

  const positionClasses = {
    'top-right': 'top-0 right-0 translate-x-1/3 -translate-y-1/3',
    'top-left': 'top-0 left-0 -translate-x-1/3 -translate-y-1/3',
    'bottom-right': 'bottom-0 right-0 translate-x-1/3 translate-y-1/3',
    'bottom-left': 'bottom-0 left-0 -translate-x-1/3 translate-y-1/3',
    'center': 'top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2',
  };

  const colorMap = {
    accent: '#0052FF',
    secondary: '#4D7CFF',
    custom: customColor || '#0052FF',
  };

  const glowColor = colorMap[color];

  return (
    <motion.div
      className={`
        absolute
        rounded-full
        blur-[150px]
        pointer-events-none
        ${sizeClasses[size]}
        ${positionClasses[position]}
        ${className}
      `}
      style={{
        background: `radial-gradient(circle, ${glowColor}, transparent)`,
        opacity,
      }}
      animate={animated ? {
        scale: [1, 1.1, 1],
        opacity: [opacity, opacity * 1.2, opacity],
      } : undefined}
      transition={animated ? {
        duration: 8,
        ease: 'easeInOut',
        repeat: Infinity,
      } : undefined}
    />
  );
};

export default RadialGlow;


