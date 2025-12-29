import React from 'react';
import { motion } from 'framer-motion';

export interface Step {
  key: string;
  title: string;
  icon?: React.ReactNode;
}

export interface StepIndicatorProps {
  steps: Step[];
  currentStep: number;
  className?: string;
}

export const StepIndicator: React.FC<StepIndicatorProps> = ({
  steps,
  currentStep,
  className = '',
}) => {
  return (
    <div className={`w-full px-4 py-3 bg-card shadow-sm ${className}`}>
      <div className="flex items-center justify-between max-w-md mx-auto">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;
          const isPending = index > currentStep;

          return (
            <React.Fragment key={step.key}>
              {/* Step Node */}
              <div className="flex flex-col items-center">
                <motion.div
                  className={`
                    w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                    transition-all duration-300
                    ${isCompleted 
                      ? 'bg-gradient-to-br from-primary to-accent text-white' 
                      : isCurrent 
                        ? 'bg-gradient-to-br from-primary to-accent text-white ring-4 ring-primary/20' 
                        : 'bg-muted text-muted-foreground'
                    }
                  `}
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ 
                    scale: isCurrent ? 1.1 : 1, 
                    opacity: 1 
                  }}
                  transition={{ duration: 0.3 }}
                >
                  {isCompleted ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    step.icon || <span>{index + 1}</span>
                  )}
                </motion.div>
                <span 
                  className={`
                    mt-1.5 text-xs font-medium transition-colors duration-300
                    ${isCurrent ? 'text-primary' : isPending ? 'text-muted-foreground' : 'text-foreground'}
                  `}
                >
                  {step.title}
                </span>
              </div>

              {/* Connector Line */}
              {index < steps.length - 1 && (
                <div className="flex-1 mx-2 h-0.5 bg-muted relative -mt-5">
                  <motion.div
                    className="absolute inset-0 bg-gradient-to-r from-primary to-accent"
                    initial={{ scaleX: 0 }}
                    animate={{ 
                      scaleX: isCompleted ? 1 : 0 
                    }}
                    style={{ transformOrigin: 'left' }}
                    transition={{ duration: 0.4, ease: 'easeOut' }}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

export default StepIndicator;

