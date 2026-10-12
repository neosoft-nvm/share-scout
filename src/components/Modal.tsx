import { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';
import type { ReactNode } from 'react';

export function Modal({ isOpen, onClose, title, subtitle, children, maxWidth = 'max-w-lg' }: {
  isOpen: boolean; onClose: () => void; title: string; subtitle?: string; children: ReactNode; maxWidth?: string;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const close = useRef(onClose); close.current = onClose;
  useEffect(() => {
    if (!isOpen) return;
    const previous = document.activeElement as HTMLElement | null;
    const focusable = () => Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex="0"]') || []);
    const target = panel.current?.querySelector<HTMLElement>('[autofocus]') || focusable()[0];
    target?.focus();
    function keydown(e: KeyboardEvent) {
      if (e.key === 'Escape') { e.stopPropagation(); close.current(); }
      if (e.key === 'Tab') {
        const elements = focusable(); const first = elements[0]; const last = elements[elements.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
      }
    }
    document.addEventListener('keydown', keydown);
    return () => { document.removeEventListener('keydown', keydown); previous?.focus(); };
  }, [isOpen]);
  if (!isOpen) return null;
  return <div className="modal-overlay"><div ref={panel} role="dialog" aria-modal="true" aria-labelledby={titleId} className={`modal-panel ${maxWidth}`}>
    <header className="modal-header"><div><h2 id={titleId}>{title}</h2>{subtitle && <p>{subtitle}</p>}</div><button type="button" className="modal-close" aria-label="Close dialog" onClick={onClose}><X size={21} /></button></header>
    <div className="modal-body">{children}</div>
  </div></div>;
}
