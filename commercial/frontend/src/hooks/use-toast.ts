/**
 * Simple toast hook for notifications
 * This is a minimal implementation for the demo
 */

import { useCallback } from 'react';

export interface Toast {
  title: string;
  description?: string;
  variant?: 'default' | 'destructive';
}

export function useToast() {
  const toast = useCallback((props: Toast) => {
    // Simple alert-based toast for MVP
    // In production, this should use a proper toast library like sonner or react-hot-toast
    const message = props.description
      ? `${props.title}\n${props.description}`
      : props.title;

    if (props.variant === 'destructive') {
      alert(`❌ ${message}`);
    } else {
      alert(`✓ ${message}`);
    }
  }, []);

  return { toast };
}
