import React, { useRef, useState } from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { cn } from '../lib/cn';

interface MagneticButtonProps extends HTMLMotionProps<"button"> {
  children: React.ReactNode;
  strength?: number;
  className?: string;
}

/**
 * A highly polished button that subtly pulls toward the cursor on hover.
 * Uses Framer Motion for smooth spring physics.
 */
export const MagneticButton: React.FC<MagneticButtonProps> = ({
  children,
  strength = 15,
  className,
  ...props
}) => {
  const ref = useRef<HTMLButtonElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  const handleMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!ref.current) return;
    const { clientX, clientY } = e;
    const { height, width, left, top } = ref.current.getBoundingClientRect();
    const centerX = left + width / 2;
    const centerY = top + height / 2;
    const x = ((clientX - centerX) / width) * strength;
    const y = ((clientY - centerY) / height) * strength;
    setPosition({ x, y });
  };

  const handleMouseLeave = () => {
    setPosition({ x: 0, y: 0 });
  };

  return (
    <motion.button
      ref={ref}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      animate={{ x: position.x, y: position.y }}
      transition={{ type: 'spring', stiffness: 150, damping: 15, mass: 0.1 }}
      className={cn('relative', className)}
      {...props}
    >
      {children}
    </motion.button>
  );
};
