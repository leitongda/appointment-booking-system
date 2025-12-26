import React from 'react';
import { motion } from 'framer-motion';
import { fadeInUp, viewportOptions } from './animations';

export interface GradientTextProps {
  children: React.ReactNode;
  as?: 'span' | 'h1' | 'h2' | 'h3' | 'p';
  showUnderline?: boolean;
  animated?: boolean;
  className?: string;
}

/**
 * GradientText - Applies the signature Electric Blue gradient to text
 * 
 * Features:
 * - Text color via background-clip technique
 * - Optional gradient underline decoration
 * - Uses Calistoga font for headings
 */
export const GradientText: React.FC<GradientTextProps> = ({
  children,
  as = 'span',
  showUnderline = false,
  animated = true,
  className = '',
}) => {
  const baseClassName = `
    relative inline-block
    bg-gradient-to-r from-accent to-accent-secondary 
    bg-clip-text text-transparent
    ${className}
  `;

  const animationProps = animated ? {
    variants: fadeInUp,
    initial: 'hidden' as const,
    whileInView: 'visible' as const,
    viewport: viewportOptions,
  } : {};

  const renderUnderline = () => showUnderline && (
    <span 
      className="
        absolute -bottom-1 left-0 
        h-3 w-full 
        rounded-sm
      "
      style={{
        background: 'linear-gradient(to right, rgba(0, 82, 255, 0.15), rgba(77, 124, 255, 0.1))',
      }}
    />
  );

  // Render different elements based on 'as' prop
  switch (as) {
    case 'h1':
      return (
        <motion.h1 className={baseClassName} {...animationProps}>
          {children}
          {renderUnderline()}
        </motion.h1>
      );
    case 'h2':
      return (
        <motion.h2 className={baseClassName} {...animationProps}>
          {children}
          {renderUnderline()}
        </motion.h2>
      );
    case 'h3':
      return (
        <motion.h3 className={baseClassName} {...animationProps}>
          {children}
          {renderUnderline()}
        </motion.h3>
      );
    case 'p':
      return (
        <motion.p className={baseClassName} {...animationProps}>
          {children}
          {renderUnderline()}
        </motion.p>
      );
    default:
      return (
        <motion.span className={baseClassName} {...animationProps}>
          {children}
          {renderUnderline()}
        </motion.span>
      );
  }
};

/**
 * GradientHeading - Convenience component for gradient headings
 * Combines display font with gradient text
 */
export interface GradientHeadingProps {
  children: React.ReactNode;
  level?: 1 | 2 | 3;
  highlightWord?: string;
  showUnderline?: boolean;
  animated?: boolean;
  className?: string;
}

export const GradientHeading: React.FC<GradientHeadingProps> = ({
  children,
  level = 1,
  highlightWord,
  showUnderline = false,
  animated = true,
  className = '',
}) => {
  const sizeClasses = {
    1: 'text-3xl md:text-4xl lg:text-5xl',
    2: 'text-2xl md:text-3xl',
    3: 'text-xl md:text-2xl',
  };

  const baseClassName = `
    font-display 
    ${sizeClasses[level]} 
    text-foreground 
    leading-tight 
    ${className}
  `;

  const animationProps = animated ? {
    variants: fadeInUp,
    initial: 'hidden' as const,
    whileInView: 'visible' as const,
    viewport: viewportOptions,
  } : {};

  // If we need to highlight a specific word
  if (highlightWord && typeof children === 'string') {
    const parts = children.split(highlightWord);
    if (parts.length === 2) {
      const content = (
        <>
          {parts[0]}
          <GradientText showUnderline={showUnderline} animated={false}>
            {highlightWord}
          </GradientText>
          {parts[1]}
        </>
      );

      switch (level) {
        case 1:
          return <motion.h1 className={baseClassName} {...animationProps}>{content}</motion.h1>;
        case 2:
          return <motion.h2 className={baseClassName} {...animationProps}>{content}</motion.h2>;
        case 3:
          return <motion.h3 className={baseClassName} {...animationProps}>{content}</motion.h3>;
      }
    }
  }

  switch (level) {
    case 1:
      return <motion.h1 className={baseClassName} {...animationProps}>{children}</motion.h1>;
    case 2:
      return <motion.h2 className={baseClassName} {...animationProps}>{children}</motion.h2>;
    case 3:
      return <motion.h3 className={baseClassName} {...animationProps}>{children}</motion.h3>;
    default:
      return <motion.h1 className={baseClassName} {...animationProps}>{children}</motion.h1>;
  }
};

export default GradientText;
