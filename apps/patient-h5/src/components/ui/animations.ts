/**
 * Framer Motion Animation Configurations
 * Following the Minimalist Modern Design System
 */

import type { Variants, Transition } from 'framer-motion';

// Custom easing curve for smooth, confident motion
export const easeOut = [0.16, 1, 0.3, 1] as const;

// Standard transition for most animations
export const standardTransition: Transition = {
  duration: 0.7,
  ease: easeOut,
};

// Quick transition for hover effects
export const quickTransition: Transition = {
  duration: 0.2,
  ease: 'easeOut',
};

/**
 * Fade in from bottom - primary entrance animation
 * Used for cards, sections, and major content blocks
 */
export const fadeInUp: Variants = {
  hidden: { 
    opacity: 0, 
    y: 28 
  },
  visible: { 
    opacity: 1, 
    y: 0, 
    transition: standardTransition 
  },
};

/**
 * Simple fade in - for subtle entrances
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
    x: -30 
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
    x: 30 
  },
  visible: { 
    opacity: 1, 
    x: 0, 
    transition: standardTransition 
  },
};

/**
 * Stagger container - wraps children with staggered animations
 * Use with children that have their own variants
 */
export const stagger: Variants = {
  hidden: {},
  visible: { 
    transition: { 
      staggerChildren: 0.1, 
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
      staggerChildren: 0.05, 
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
  margin: '-60px' 
};

/**
 * Floating animation for decorative elements
 * Continuous, slow, and subtle
 */
export const floatAnimation = {
  y: [0, -10, 0],
  transition: {
    duration: 5,
    ease: 'easeInOut',
    repeat: Infinity,
  },
};

/**
 * Delayed floating animation
 */
export const floatAnimationDelayed = {
  y: [0, -10, 0],
  transition: {
    duration: 4,
    ease: 'easeInOut',
    repeat: Infinity,
    delay: 0.5,
  },
};

/**
 * Pulse animation for indicators and dots
 */
export const pulseAnimation = {
  scale: [1, 1.3, 1],
  opacity: [1, 0.7, 1],
  transition: {
    duration: 2,
    ease: 'easeInOut' as const,
    repeat: Infinity,
  },
};

/**
 * Slow rotation for decorative elements
 */
export const rotateAnimation = {
  rotate: 360,
  transition: {
    duration: 60,
    ease: 'linear',
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
  y: -4,
  transition: quickTransition,
};

/**
 * Icon hover animation
 */
export const iconHover = {
  scale: 1.1,
  transition: quickTransition,
};

/**
 * Arrow slide animation (for CTAs)
 */
export const arrowSlide = {
  x: 4,
  transition: quickTransition,
};


