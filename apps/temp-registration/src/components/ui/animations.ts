/**
 * Framer Motion Animation Configurations
 * 临时挂号应用动画配置
 */

import type { Variants, Transition } from 'framer-motion';

// Custom easing curve for smooth, confident motion
export const easeOut = [0.16, 1, 0.3, 1] as const;

// Standard transition for most animations
export const standardTransition: Transition = {
  duration: 0.5,
  ease: easeOut,
};

// Quick transition for hover effects
export const quickTransition: Transition = {
  duration: 0.2,
  ease: 'easeOut',
};

/**
 * Fade in from bottom - primary entrance animation
 */
export const fadeInUp: Variants = {
  hidden: { 
    opacity: 0, 
    y: 20 
  },
  visible: { 
    opacity: 1, 
    y: 0, 
    transition: standardTransition 
  },
};

/**
 * Simple fade in
 */
export const fadeIn: Variants = {
  hidden: { 
    opacity: 0 
  },
  visible: { 
    opacity: 1, 
    transition: standardTransition 
  },
};

/**
 * Scale in - for buttons and interactive elements
 */
export const scaleIn: Variants = {
  hidden: { 
    opacity: 0, 
    scale: 0.95 
  },
  visible: { 
    opacity: 1, 
    scale: 1, 
    transition: standardTransition 
  },
};

/**
 * Slide in from left
 */
export const slideInLeft: Variants = {
  hidden: { 
    opacity: 0, 
    x: -20 
  },
  visible: { 
    opacity: 1, 
    x: 0, 
    transition: standardTransition 
  },
};

/**
 * Slide in from right
 */
export const slideInRight: Variants = {
  hidden: { 
    opacity: 0, 
    x: 20 
  },
  visible: { 
    opacity: 1, 
    x: 0, 
    transition: standardTransition 
  },
};

/**
 * Stagger container
 */
export const stagger: Variants = {
  hidden: {},
  visible: { 
    transition: { 
      staggerChildren: 0.08, 
      delayChildren: 0.1 
    } 
  },
};

/**
 * Stagger with faster timing
 */
export const staggerFast: Variants = {
  hidden: {},
  visible: { 
    transition: { 
      staggerChildren: 0.04, 
      delayChildren: 0.05 
    } 
  },
};

/**
 * Viewport options for scroll-triggered animations
 */
export const viewportOptions = { 
  once: true, 
  amount: 0.15, 
  margin: '-40px' 
};

/**
 * Pulse animation for indicators
 */
export const pulseAnimation = {
  scale: [1, 1.2, 1],
  opacity: [1, 0.8, 1],
  transition: {
    duration: 2,
    ease: 'easeInOut' as const,
    repeat: Infinity,
  },
};

/**
 * Button hover animation
 */
export const buttonHover = {
  y: -2,
  transition: quickTransition,
};

/**
 * Button tap animation
 */
export const buttonTap = {
  scale: 0.98,
};

/**
 * Card hover animation
 */
export const cardHover = {
  y: -3,
  transition: quickTransition,
};

/**
 * Page transition variants
 */
export const pageTransition: Variants = {
  initial: {
    opacity: 0,
    x: 20,
  },
  enter: {
    opacity: 1,
    x: 0,
    transition: {
      duration: 0.3,
      ease: easeOut,
    },
  },
  exit: {
    opacity: 0,
    x: -20,
    transition: {
      duration: 0.2,
    },
  },
};

