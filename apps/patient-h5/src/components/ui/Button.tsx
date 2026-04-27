import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { buttonHover, buttonTap, arrowSlide } from './animations';

export interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'children'> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  block?: boolean;
  /** aria-label for icon-only buttons */
  'aria-label'?: string;
  children: React.ReactNode;
}

const variantStyles = {
  primary: `
    bg-gradient-to-r from-accent to-accent-secondary 
    text-accent-foreground 
    shadow-sm 
    hover:shadow-accent-lg hover:brightness-110
    active:scale-[0.98]
  `,
  secondary: `
    bg-muted 
    text-foreground 
    hover:bg-muted/80
    active:scale-[0.98]
  `,
  ghost: `
    bg-transparent 
    text-muted-foreground 
    hover:text-foreground hover:bg-muted/50
  `,
  outline: `
    bg-transparent 
    border border-border 
    text-foreground 
    hover:border-accent/30 hover:shadow-sm
    active:scale-[0.98]
  `,
};

const sizeStyles = {
  sm: 'h-10 px-4 text-sm rounded-lg',
  md: 'h-12 px-6 text-base rounded-xl',
  lg: 'h-14 px-8 text-lg rounded-xl',
};

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  iconPosition = 'left',
  block = false,
  children,
  className = '',
  disabled,
  'aria-label': ariaLabel,
  ...props
}) => {
  const isDisabled = disabled || loading;

  return (
    <motion.button
      className={`
        inline-flex items-center justify-center gap-2
        font-medium
        transition-all duration-200
        touch-target
        ${variantStyles[variant]}
        ${sizeStyles[size]}
        ${block ? 'w-full' : ''}
        ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        ${className}
      `}
      whileHover={isDisabled ? undefined : buttonHover}
      whileTap={isDisabled ? undefined : buttonTap}
      disabled={isDisabled}
      aria-disabled={isDisabled || undefined}
      aria-label={ariaLabel}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && (
        <svg
          className="animate-spin h-5 w-5"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
      {icon && iconPosition === 'left' && !loading && (
        <span className="flex-shrink-0">{icon}</span>
      )}
      <span>{children}</span>
      {icon && iconPosition === 'right' && !loading && (
        <motion.span 
          className="flex-shrink-0"
          whileHover={arrowSlide}
        >
          {icon}
        </motion.span>
      )}
    </motion.button>
  );
};

export default Button;


