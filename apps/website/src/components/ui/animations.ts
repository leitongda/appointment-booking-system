/**
 * Framer Motion Animation Configurations
 * Minimalist Modern Design System
 */

import type { Variants, Transition } from 'framer-motion';

export const easeOut = [0.16, 1, 0.3, 1] as const;

export const standardTransition: Transition = {
  duration: 0.7,
  ease: easeOut,
};

export const quickTransition: Transition = {
  duration: 0.2,
  ease: 'easeOut',
};

export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 28 },
  visible: { opacity: 1, y: 0, transition: standardTransition },
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: standardTransition },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1, transition: standardTransition },
};

export const slideInLeft: Variants = {
  hidden: { opacity: 0, x: -30 },
  visible: { opacity: 1, x: 0, transition: standardTransition },
};

export const slideInRight: Variants = {
  hidden: { opacity: 0, x: 30 },
  visible: { opacity: 1, x: 0, transition: standardTransition },
};

export const stagger: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1, delayChildren: 0.1 } },
};

export const viewportOptions = {
  once: true,
  amount: 0.15,
  margin: '-60px',
};

export const floatAnimation = {
  y: [0, -10, 0],
  transition: { duration: 5, ease: 'easeInOut' as const, repeat: Infinity },
};

export const floatAnimationDelayed = {
  y: [0, -10, 0],
  transition: { duration: 4, ease: 'easeInOut' as const, repeat: Infinity, delay: 0.5 },
};

export const pulseAnimation = {
  scale: [1, 1.3, 1],
  opacity: [1, 0.7, 1],
  transition: { duration: 2, ease: 'easeInOut' as const, repeat: Infinity },
};

export const rotateAnimation = {
  rotate: 360,
  transition: { duration: 60, ease: 'linear' as const, repeat: Infinity },
};

export const buttonHover = { y: -2, transition: quickTransition };
export const buttonTap = { scale: 0.98 };
export const cardHover = { y: -4, transition: quickTransition };
export const iconHover = { scale: 1.1, transition: quickTransition };
export const arrowSlide = { x: 4, transition: quickTransition };
