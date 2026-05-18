import { type HTMLAttributes, forwardRef } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { fadeInUp, cardHover, viewportOptions } from './animations';

type Variant = 'default' | 'elevated' | 'gradient-border' | 'flat';
type Padding = 'sm' | 'md' | 'lg';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: Variant;
  padding?: Padding;
  hoverable?: boolean;
  animate?: boolean;
}

const variantStyles: Record<Variant, string> = {
  default: 'bg-card border border-border rounded-2xl shadow-md',
  elevated: 'bg-card border border-border rounded-2xl shadow-lg hover:shadow-xl',
  'gradient-border': '',
  flat: 'bg-card rounded-2xl',
};

const paddingStyles: Record<Padding, string> = {
  sm: 'p-5',
  md: 'p-7',
  lg: 'p-10',
};

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ variant = 'default', padding = 'md', hoverable = false, animate = false, className, children, ...props }, ref) => {
    const content = (
      <div
        ref={ref}
        className={cn(
          'transition-all duration-300',
          variantStyles[variant],
          paddingStyles[padding],
          hoverable && 'hover:-translate-y-1 hover:shadow-xl',
          className,
        )}
        {...props}
      >
        {children}
      </div>
    );

    if (variant === 'gradient-border') {
      const wrapped = (
        <div className="rounded-2xl bg-gradient-to-br from-accent via-accent-secondary to-accent p-[2px]">
          <div
            ref={ref}
            className={cn(
              'h-full w-full rounded-[calc(16px-2px)] bg-card transition-all duration-300',
              paddingStyles[padding],
              hoverable && 'hover:-translate-y-1 hover:shadow-xl',
              className,
            )}
            {...props}
          >
            {children}
          </div>
        </div>
      );
      if (animate) {
        return (
          <motion.div initial="hidden" whileInView="visible" viewport={viewportOptions} variants={fadeInUp}>
            {wrapped}
          </motion.div>
        );
      }
      return wrapped;
    }

    if (animate) {
      return (
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={fadeInUp}
          whileHover={hoverable ? cardHover : undefined}
        >
          {content}
        </motion.div>
      );
    }

    if (hoverable) {
      return (
        <motion.div whileHover={cardHover}>
          {content}
        </motion.div>
      );
    }

    return content;
  },
);

Card.displayName = 'Card';
