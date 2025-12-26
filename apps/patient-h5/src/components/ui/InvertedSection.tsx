import React from 'react';
import { motion } from 'framer-motion';
import { fadeIn, viewportOptions } from './animations';

export interface InvertedSectionProps {
  children: React.ReactNode;
  showDotPattern?: boolean;
  showGlow?: boolean;
  glowPosition?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  padding?: 'sm' | 'md' | 'lg';
  animated?: boolean;
  className?: string;
}

/**
 * InvertedSection - A dark background section with optional textures
 * 
 * Features:
 * - Deep slate background (foreground color)
 * - White/light text
 * - Optional dot pattern texture at 3% opacity
 * - Optional radial glow decoration
 */
export const InvertedSection: React.FC<InvertedSectionProps> = ({
  children,
  showDotPattern = true,
  showGlow = false,
  glowPosition = 'top-right',
  padding = 'md',
  animated = true,
  className = '',
}) => {
  const paddingClasses = {
    sm: 'py-6 px-4',
    md: 'py-8 px-4',
    lg: 'py-12 px-4',
  };

  const glowPositionClasses = {
    'top-right': 'top-0 right-0 translate-x-1/2 -translate-y-1/2',
    'top-left': 'top-0 left-0 -translate-x-1/2 -translate-y-1/2',
    'bottom-right': 'bottom-0 right-0 translate-x-1/2 translate-y-1/2',
    'bottom-left': 'bottom-0 left-0 -translate-x-1/2 translate-y-1/2',
  };

  return (
    <motion.section
      className={`
        relative overflow-hidden
        bg-foreground text-white
        ${paddingClasses[padding]}
        ${className}
      `}
      variants={animated ? fadeIn : undefined}
      initial={animated ? 'hidden' : undefined}
      whileInView={animated ? 'visible' : undefined}
      viewport={animated ? viewportOptions : undefined}
    >
      {/* Dot pattern texture overlay */}
      {showDotPattern && (
        <div 
          className="absolute inset-0 opacity-[0.03] pointer-events-none"
          style={{
            backgroundImage: 'radial-gradient(circle, rgba(255, 255, 255, 0.5) 1px, transparent 1px)',
            backgroundSize: '32px 32px',
          }}
        />
      )}

      {/* Radial glow decoration */}
      {showGlow && (
        <div 
          className={`
            absolute w-64 h-64 
            rounded-full 
            blur-[150px] 
            opacity-[0.06]
            pointer-events-none
            ${glowPositionClasses[glowPosition]}
          `}
          style={{
            background: 'radial-gradient(circle, #0052FF, transparent)',
          }}
        />
      )}

      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </motion.section>
  );
};

export default InvertedSection;


