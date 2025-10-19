"use client";
import { useEffect, useState } from "react";

export type Toast = { id: number; msg: string; type?: 'info'|'success'|'error' };

export function toast(msg: string, type: 'info'|'success'|'error' = 'info'){
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent('toast', { detail: { msg, type } }));
}

export default function Toaster(){
  const [items, setItems] = useState<Toast[]>([]);
  useEffect(() => {
    function onEvt(e: Event){
      const ce = e as CustomEvent; const detail = (ce.detail || {}) as any;
      const id = Date.now() + Math.random();
      const t: Toast = { id, msg: String(detail.msg||''), type: detail.type || 'info' };
      setItems(prev => [...prev, t]);
      setTimeout(() => setItems(prev => prev.filter(x => x.id !== id)), 3200);
    }
    window.addEventListener('toast', onEvt as any);
    return () => window.removeEventListener('toast', onEvt as any);
  }, []);
  const bgFor = (t: Toast) => t.type==='success' ? '#ecfdf5' : t.type==='error' ? '#fee2e2' : '#f1f5f9';
  const fgFor = (t: Toast) => t.type==='success' ? '#14532d' : t.type==='error' ? '#991b1b' : '#0f172a';
  return (
    <div style={{position:'fixed', right:12, top:12, zIndex:9999, display:'flex', flexDirection:'column', gap:8}}>
      {items.map(t => (
        <div key={t.id} style={{background:bgFor(t), color:fgFor(t), border:'1px solid #e5e7eb', padding:'8px 12px', borderRadius:8, minWidth:220, boxShadow:'0 2px 6px rgba(0,0,0,0.08)'}}>
          {t.msg}
        </div>
      ))}
    </div>
  );
}

