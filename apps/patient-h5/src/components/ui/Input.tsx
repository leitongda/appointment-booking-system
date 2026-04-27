import React, { forwardRef } from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  variant?: 'default' | 'filled';
}

export const Input = forwardRef<HTMLInputElement, InputProps>(({
  label,
  error,
  hint,
  leftIcon,
  rightIcon,
  variant = 'default',
  className = '',
  id,
  ...props
}, ref) => {
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
  const hintId = error || hint ? `${inputId}-hint` : undefined;

  const variantStyles = {
    default: `
      bg-transparent 
      border border-border 
      focus:border-accent focus:ring-2 focus:ring-accent/20
    `,
    filled: `
      bg-muted 
      border border-transparent 
      focus:border-accent focus:ring-2 focus:ring-accent/20
    `,
  };

  return (
    <div className="w-full">
      {label && (
        <label 
          htmlFor={inputId}
          className="block text-sm font-medium text-foreground mb-2"
        >
          {label}
        </label>
      )}
      <div className="relative">
        {leftIcon && (
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground">
            {leftIcon}
          </div>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={hintId}
          className={`
            w-full
            h-12
            px-4
            ${leftIcon ? 'pl-11' : ''}
            ${rightIcon ? 'pr-11' : ''}
            rounded-xl
            text-foreground
            placeholder:text-muted-foreground/50
            transition-all duration-200
            outline-none
            touch-target
            ${variantStyles[variant]}
            ${error ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20' : ''}
            ${className}
          `}
          {...props}
        />
        {rightIcon && (
          <div className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground">
            {rightIcon}
          </div>
        )}
      </div>
      {(error || hint) && (
        <p id={hintId} className={`mt-2 text-sm ${error ? 'text-red-500' : 'text-muted-foreground'}`}>
          {error || hint}
        </p>
      )}
    </div>
  );
});

Input.displayName = 'Input';

// Textarea variant
export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
  variant?: 'default' | 'filled';
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(({
  label,
  error,
  hint,
  variant = 'default',
  className = '',
  id,
  rows = 4,
  ...props
}, ref) => {
  const textareaId = id || `textarea-${Math.random().toString(36).substr(2, 9)}`;
  const hintId = error || hint ? `${textareaId}-hint` : undefined;

  const variantStyles = {
    default: `
      bg-transparent 
      border border-border 
      focus:border-accent focus:ring-2 focus:ring-accent/20
    `,
    filled: `
      bg-muted 
      border border-transparent 
      focus:border-accent focus:ring-2 focus:ring-accent/20
    `,
  };

  return (
    <div className="w-full">
      {label && (
        <label 
          htmlFor={textareaId}
          className="block text-sm font-medium text-foreground mb-2"
        >
          {label}
        </label>
      )}
      <textarea
        ref={ref}
        id={textareaId}
        rows={rows}
        aria-invalid={error ? true : undefined}
        aria-describedby={hintId}
        className={`
          w-full
          p-4
          rounded-xl
          text-foreground
          placeholder:text-muted-foreground/50
          transition-all duration-200
          outline-none
          resize-none
          ${variantStyles[variant]}
          ${error ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20' : ''}
          ${className}
        `}
        {...props}
      />
      {(error || hint) && (
        <p id={hintId} className={`mt-2 text-sm ${error ? 'text-red-500' : 'text-muted-foreground'}`}>
          {error || hint}
        </p>
      )}
    </div>
  );
});

Textarea.displayName = 'Textarea';

export default Input;


