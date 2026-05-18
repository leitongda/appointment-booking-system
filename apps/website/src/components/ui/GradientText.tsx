import { type ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface GradientTextProps {
  children: ReactNode;
  className?: string;
}

export function GradientText({ children, className }: GradientTextProps) {
  return <span className={cn('gradient-text', className)}>{children}</span>;
}

interface GradientHeadingProps {
  children: ReactNode;
  level?: 1 | 2 | 3;
  underline?: boolean;
  className?: string;
}

export function GradientHeading({ children, level = 2, underline = false, className }: GradientHeadingProps) {
  const Tag = `h${level}` as keyof JSX.IntrinsicElements;
  const sizeClasses = {
    1: 'text-[2.75rem] md:text-6xl lg:text-[5.25rem] leading-[1.05] tracking-tight',
    2: 'text-3xl md:text-[3.25rem] leading-[1.15]',
    3: 'text-xl md:text-2xl',
  };

  return (
    <Tag className={cn('relative font-display text-foreground', sizeClasses[level], className)}>
      {children}
      {underline && <span className="gradient-underline" />}
    </Tag>
  );
}
