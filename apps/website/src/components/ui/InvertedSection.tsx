import { type HTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface InvertedSectionProps extends HTMLAttributes<HTMLElement> {
  as?: 'section' | 'div';
}

export const InvertedSection = forwardRef<HTMLElement, InvertedSectionProps>(
  ({ as: Tag = 'section', className, children, ...props }, ref) => {
    return (
      <Tag
        ref={ref as any}
        className={cn('relative overflow-hidden bg-foreground text-background', className)}
        {...props}
      >
        {/* Dot pattern texture */}
        <div className="pointer-events-none absolute inset-0 bg-dot-pattern" />
        {/* Content */}
        <div className="relative z-10">{children}</div>
      </Tag>
    );
  },
);

InvertedSection.displayName = 'InvertedSection';
