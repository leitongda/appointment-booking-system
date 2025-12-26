import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { fadeInUp, cardHover, viewportOptions } from './animations';

export interface CardProps extends Omit<HTMLMotionProps<'div'>, 'children'> {
  variant?: 'default' | 'elevated' | 'gradient-border' | 'flat';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hoverable?: boolean;
  animated?: boolean;
  children: React.ReactNode;
}

const variantStyles = {
  default: 'bg-card border border-border rounded-xl shadow-md',
  elevated: 'bg-card border border-border rounded-xl shadow-lg',
  'gradient-border': '', // Handled specially with wrapper
  flat: 'bg-muted rounded-xl',
};

const paddingStyles = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export const Card: React.FC<CardProps> = ({
  variant = 'default',
  padding = 'md',
  hoverable = false,
  animated = true,
  children,
  className = '',
  ...props
}) => {
  // Gradient border variant needs special wrapper
  if (variant === 'gradient-border') {
    return (
      <motion.div
        className={`rounded-xl bg-gradient-to-br from-accent via-accent-secondary to-accent p-[2px] ${className}`}
        variants={animated ? fadeInUp : undefined}
        initial={animated ? 'hidden' : undefined}
        whileInView={animated ? 'visible' : undefined}
        viewport={animated ? viewportOptions : undefined}
        whileHover={hoverable ? cardHover : undefined}
        {...props}
      >
        <div className={`
          h-full w-full 
          rounded-[calc(12px-2px)] 
          bg-card
          ${paddingStyles[padding]}
        `}>
          {children}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      className={`
        ${variantStyles[variant]}
        ${paddingStyles[padding]}
        transition-all duration-200
        ${hoverable ? 'hover:shadow-xl' : ''}
        ${className}
      `}
      variants={animated ? fadeInUp : undefined}
      initial={animated ? 'hidden' : undefined}
      whileInView={animated ? 'visible' : undefined}
      viewport={animated ? viewportOptions : undefined}
      whileHover={hoverable ? cardHover : undefined}
      {...props}
    >
      {children}
    </motion.div>
  );
};

// Card Header component
export interface CardHeaderProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  subtitle,
  action,
  className = '',
}) => (
  <div className={`flex items-center justify-between mb-4 ${className}`}>
    <div>
      <h3 className="font-semibold text-foreground text-lg">{title}</h3>
      {subtitle && (
        <p className="text-muted-foreground text-sm mt-1">{subtitle}</p>
      )}
    </div>
    {action && <div>{action}</div>}
  </div>
);

// Card Content component
export interface CardContentProps {
  children: React.ReactNode;
  className?: string;
}

export const CardContent: React.FC<CardContentProps> = ({
  children,
  className = '',
}) => (
  <div className={className}>{children}</div>
);

// Card Footer component
export interface CardFooterProps {
  children: React.ReactNode;
  className?: string;
}

export const CardFooter: React.FC<CardFooterProps> = ({
  children,
  className = '',
}) => (
  <div className={`mt-4 pt-4 border-t border-border ${className}`}>
    {children}
  </div>
);

export default Card;


