import * as React from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';

interface TooltipContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
  triggerRef: React.RefObject<HTMLElement | null>;
}

const TooltipContext = React.createContext<TooltipContextValue | null>(null);

interface TooltipProps {
  children: React.ReactNode;
}

export function Tooltip({ children }: TooltipProps) {
  const [open, setOpen] = React.useState(false);
  const triggerRef = React.useRef<HTMLElement | null>(null);

  return (
    <TooltipContext.Provider value={{ open, setOpen, triggerRef }}>
      {children}
    </TooltipContext.Provider>
  );
}

interface TooltipTriggerProps {
  children: React.ReactElement;
  asChild?: boolean;
}

export function TooltipTrigger({ children, asChild }: TooltipTriggerProps) {
  const context = React.useContext(TooltipContext);
  if (!context) throw new Error('TooltipTrigger must be used within Tooltip');

  const { setOpen, triggerRef } = context;

  const handleMouseEnter = () => setOpen(true);
  const handleMouseLeave = () => setOpen(false);
  const handleFocus = () => setOpen(true);
  const handleBlur = () => setOpen(false);

  const setRef = React.useCallback((node: HTMLElement | null) => {
    triggerRef.current = node;
  }, [triggerRef]);

  if (asChild && React.isValidElement(children)) {
    const childProps: Record<string, unknown> = {
      onMouseEnter: handleMouseEnter,
      onMouseLeave: handleMouseLeave,
      onFocus: handleFocus,
      onBlur: handleBlur,
    };
    
    // Handle ref separately - only support function refs to avoid modifying immutable ref objects
    const originalRef = (children as React.ReactElement & { ref?: React.Ref<HTMLElement> }).ref;
    if (originalRef && typeof originalRef === 'function') {
      childProps.ref = (node: HTMLElement | null) => {
        triggerRef.current = node;
        originalRef(node);
      };
    } else {
      childProps.ref = setRef;
    }

    return React.cloneElement(children, childProps);
  }

  return (
    <div
      ref={setRef}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocus={handleFocus}
      onBlur={handleBlur}
    >
      {children}
    </div>
  );
}

interface TooltipPanelProps {
  children: React.ReactNode;
  side?: 'top' | 'right' | 'bottom' | 'left';
  sideOffset?: number;
  align?: 'start' | 'center' | 'end';
  className?: string;
}

export function TooltipPanel({ 
  children, 
  side = 'top', 
  sideOffset = 5,
  align = 'center',
  className = '',
}: TooltipPanelProps) {
  const context = React.useContext(TooltipContext);
  if (!context) throw new Error('TooltipPanel must be used within Tooltip');

  const { open, triggerRef } = context;
  const [position, setPosition] = React.useState({ top: 0, left: 0 });
  const panelRef = React.useRef<HTMLDivElement>(null);

  const updatePosition = React.useCallback(() => {
    if (open && triggerRef.current && panelRef.current) {
      const triggerRect = triggerRef.current.getBoundingClientRect();
      const panelRect = panelRef.current.getBoundingClientRect();
      
      let top = 0;
      let left = 0;

      switch (side) {
        case 'top':
          top = triggerRect.top - panelRect.height - sideOffset;
          left = triggerRect.left + (triggerRect.width - panelRect.width) / 2;
          break;
        case 'bottom':
          top = triggerRect.bottom + sideOffset;
          left = triggerRect.left + (triggerRect.width - panelRect.width) / 2;
          break;
        case 'left':
          top = triggerRect.top + (triggerRect.height - panelRect.height) / 2;
          left = triggerRect.left - panelRect.width - sideOffset;
          break;
        case 'right':
          top = triggerRect.top + (triggerRect.height - panelRect.height) / 2;
          left = triggerRect.right + sideOffset;
          break;
      }

      // Adjust for align
      if (align === 'start' && (side === 'top' || side === 'bottom')) {
        left = triggerRect.left;
      } else if (align === 'end' && (side === 'top' || side === 'bottom')) {
        left = triggerRect.right - panelRect.width;
      }

      setPosition({ top, left });
    }
  }, [open, side, sideOffset, align, triggerRef]);

  React.useEffect(() => {
    if (open) {
      // Use requestAnimationFrame to ensure DOM is updated
      const timer = requestAnimationFrame(() => {
        updatePosition();
      });
      return () => cancelAnimationFrame(timer);
    }
  }, [open, updatePosition]);

  React.useEffect(() => {
    if (open) {
      const handleScroll = () => updatePosition();
      const handleResize = () => updatePosition();
      
      window.addEventListener('scroll', handleScroll, true);
      window.addEventListener('resize', handleResize);
      
      return () => {
        window.removeEventListener('scroll', handleScroll, true);
        window.removeEventListener('resize', handleResize);
      };
    }
  }, [open, updatePosition]);

  return (
    <TooltipPortal>
      <AnimatePresence>
        {open && (
          <motion.div
            ref={panelRef}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            style={{
              position: 'fixed',
              top: position.top,
              left: position.left,
              zIndex: 50,
            }}
            className={className}
          >
            <div className="text-sm text-gray-200 bg-indigo-600/20 border border-[#3a3a60] rounded-md py-1.5 shadow-xl" style={{ padding: '10px' }}>
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </TooltipPortal>
  );
}

export function TooltipPortal({ children }: { children: React.ReactNode }) {
  return createPortal(children, document.body);
}

export function TooltipArrow() {
  return null;
}
