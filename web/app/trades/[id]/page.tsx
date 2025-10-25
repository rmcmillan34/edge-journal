"use client";
import React, { useEffect, useRef, useState } from "react";

type Attachment = {
  id: number;
  filename: string;
  mime_type?: string;
  size_bytes?: number;
  timeframe?: string;
  state?: string;
  view?: string;
  caption?: string;
  reviewed: boolean;
  thumb_available?: boolean | null;
  thumb_url?: string | null;
  sort_order?: number | null;
};
type TradeDetail = {
  id: number; account_name?: string | null; symbol?: string | null; side: string;
  qty_units?: number | null; entry_price?: number | null; exit_price?: number | null;
  open_time_utc?: string | null; close_time_utc?: string | null; net_pnl?: number | null;
  external_trade_id?: string | null; notes_md?: string | null; post_analysis_md?: string | null; reviewed: boolean;
  attachments: Attachment[];
};

export default function TradeDetailPage({ params }:{ params: { id: string } }){
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const [token, setToken] = useState<string>("");
  const [data, setData] = useState<TradeDetail | null>(null);
  const [tab, setTab] = useState<'overview'|'notes'|'attachments'|'playbook'>("overview");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [notes, setNotes] = useState("");
  const [postNotes, setPostNotes] = useState("");
  const notesRef = useRef<HTMLTextAreaElement | null>(null);
  const [attMeta, setAttMeta] = useState({ timeframe:"", state:"", view:"", caption:"", reviewed:false });
  const [files, setFiles] = useState<FileList | null>(null);
  const [tpls, setTpls] = useState<any[]>([]);
  const [tplId, setTplId] = useState<number | "">("");
  const [tplChecks, setTplChecks] = useState<Record<number, boolean>>({});
  const [attSel, setAttSel] = useState<number[]>([]);
  const [reorderMode, setReorderMode] = useState(false);
  const [editMap, setEditMap] = useState<Record<number, {timeframe:string; state:string; view:string; caption:string; reviewed:boolean} | null>>({});

  useEffect(()=>{ try { setToken(localStorage.getItem("ej_token") || ""); } catch{} },[]);
  useEffect(()=>{ if (token){ reload(); loadTemplates(); loadPlaybookTemplates(); loadPlaybookResponses(); } }, [token]);

  // Cmd/Ctrl+S to save notes; Esc to exit reorder mode
  useEffect(()=>{
    function onKey(e: KeyboardEvent){
      if ((e.key === 's' || e.key === 'S') && (e.metaKey || e.ctrlKey)){
        e.preventDefault();
        saveNotes();
      }
      if (e.key === 'Escape' && reorderMode){
        e.preventDefault();
        setReorderMode(false);
      }
    }
    window.addEventListener('keydown', onKey);
    return ()=> window.removeEventListener('keydown', onKey);
  }, [reorderMode, notes, postNotes, token]);

  async function loadTemplates(){
    try{
      const r = await fetch(`${API_BASE}/templates?target=trade`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (r.ok){ const j = await r.json(); setTpls(Array.isArray(j)?j:[]); }
    }catch{}
  }

  // --- Playbooks (M5) ---
  const [pbTemplates, setPbTemplates] = useState<any[]>([]);
  const [pbTplId, setPbTplId] = useState<number | "">("");
  const [pbValues, setPbValues] = useState<Record<string, any>>({});
  const [pbComments, setPbComments] = useState<Record<string, string>>({});
  const [pbEval, setPbEval] = useState<{ compliance_score:number; grade:string; risk_cap_pct:number; cap_breakdown:any }|null>(null);
  const [pbSaving, setPbSaving] = useState(false);
  const [pbResponses, setPbResponses] = useState<any[]>([]);
  const [pbCurrentRespId, setPbCurrentRespId] = useState<number | null>(null);
  const [pbEvidence, setPbEvidence] = useState<any[]>([]);
  const [pbEvidenceField, setPbEvidenceField] = useState<string>("");
  const [pbEvidenceUrl, setPbEvidenceUrl] = useState<string>("");
  const [pbEvidenceNote, setPbEvidenceNote] = useState<string>("");
  const [pbWarn, setPbWarn] = useState<string | null>(null);
  const [pbJournalDate, setPbJournalDate] = useState<string>("");
  const [pbJournalAtts, setPbJournalAtts] = useState<any[]>([]);
  const [pbCopySelectEvidenceId, setPbCopySelectEvidenceId] = useState<number | "">("");
  const [pbCopyFields, setPbCopyFields] = useState<Record<string, boolean>>({});
  const [expIncludePb, setExpIncludePb] = useState(true);
  const [expEvidence, setExpEvidence] = useState<'none'|'links'|'thumbs'|'full'>('links');
  
  async function exportMarkdown(){
    try{
      const qs = new URLSearchParams();
      if (!expIncludePb) qs.set('include_playbook','false');
      if (expEvidence !== 'links') qs.set('evidence', expEvidence);
      const r = await fetch(`${API_BASE}/trades/${params.id}/export.md?${qs.toString()}`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      const txt = await r.text();
      if (!r.ok) throw new Error(`Export failed: ${r.status}`);
      const blob = new Blob([txt], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `trade_${params.id}.md`; a.click(); setTimeout(()=>URL.revokeObjectURL(url), 4000);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function exportPdf(){
    try{
      const qs = new URLSearchParams();
      if (!expIncludePb) qs.set('include_playbook','false');
      if (expEvidence !== 'links') qs.set('evidence', expEvidence);
      const r = await fetch(`${API_BASE}/trades/${params.id}/export.pdf?${qs.toString()}`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (r.status === 501){
        const j = await r.json().catch(()=>({detail:'Not implemented'}));
        setError(j.detail || 'PDF not implemented');
        return;
      }
      const blob = await r.blob();
      if (!r.ok) throw new Error(`Export failed: ${r.status}`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `trade_${params.id}.pdf`; a.click(); setTimeout(()=>URL.revokeObjectURL(url), 4000);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function loadPlaybookTemplates(){
    try{
      const r = await fetch(`${API_BASE}/playbooks/templates?purpose=post`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (r.ok){ const j = await r.json(); setPbTemplates(Array.isArray(j)?j:[]); }
    }catch{}
  }

  async function loadPlaybookResponses(){
    try{
      const r = await fetch(`${API_BASE}/trades/${params.id}/playbook-responses`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (r.ok){ const j = await r.json(); setPbResponses(Array.isArray(j)?j:[]); const latest = (Array.isArray(j) && j.length) ? j[0] : null; setPbCurrentRespId(latest ? latest.id : null); if (latest) await loadEvidence(latest.id); }
    }catch{}
  }

  async function loadEvidence(respId:number){
    try{
      const r = await fetch(`${API_BASE}/playbook-responses/${respId}/evidence`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (r.ok){ const j = await r.json(); setPbEvidence(Array.isArray(j)?j:[]); }
    }catch{}
  }

  async function addEvidenceUrl(){
    if (!pbCurrentRespId || !pbEvidenceField || !pbEvidenceUrl){ setError('Select field and enter URL'); return; }
    try{
      const body = { field_key: pbEvidenceField, source_kind:'url', url: pbEvidenceUrl, note: pbEvidenceNote };
      const r = await fetch(`${API_BASE}/playbook-responses/${pbCurrentRespId}/evidence`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(body) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Add failed: ${r.status}`);
      setPbEvidenceField(""); setPbEvidenceUrl(""); setPbEvidenceNote("");
      await loadEvidence(pbCurrentRespId);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function addEvidenceTradeAttachment(attId:number){
    if (!pbCurrentRespId || !pbEvidenceField){ setError('Select field'); return; }
    try{
      const body = { field_key: pbEvidenceField, source_kind:'trade', source_id: attId };
      const r = await fetch(`${API_BASE}/playbook-responses/${pbCurrentRespId}/evidence`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(body) });
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Add failed: ${r.status}`); }
      await loadEvidence(pbCurrentRespId);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function loadJournalAttachments(){
    if (!pbJournalDate){ setError('Enter journal date'); return; }
    try{
      const r = await fetch(`${API_BASE}/journal/${pbJournalDate}`, { headers: token ? { Authorization:`Bearer ${token}` } : undefined });
      if (r.status === 404){ setPbJournalAtts([]); return; }
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Failed: ${r.status}`);
      const jid = j.id;
      const ra = await fetch(`${API_BASE}/journal/${jid}/attachments`, { headers: token ? { Authorization:`Bearer ${token}` } : undefined });
      const ja = await ra.json(); if (!ra.ok) throw new Error(ja.detail || `Failed: ${ra.status}`);
      setPbJournalAtts(Array.isArray(ja)?ja:[]);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function addEvidenceJournalAttachment(att:any){
    if (!pbCurrentRespId || !pbEvidenceField){ setError('Select field'); return; }
    try{
      const body = { field_key: pbEvidenceField, source_kind:'journal', source_id: att.id };
      const r = await fetch(`${API_BASE}/playbook-responses/${pbCurrentRespId}/evidence`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(body) });
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Add failed: ${r.status}`); }
      await loadEvidence(pbCurrentRespId);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function removeEvidence(eid:number){
    if (!pbCurrentRespId) return;
    try{
      const r = await fetch(`${API_BASE}/playbook-responses/${pbCurrentRespId}/evidence/${eid}`, { method:'DELETE', headers:{ Authorization:`Bearer ${token}` }});
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Delete failed: ${r.status}`); }
      await loadEvidence(pbCurrentRespId);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function copyEvidenceToFields(ev:any){
    if (!pbCurrentRespId) return;
    const tpl = pbTemplates.find((t:any)=> t.id===pbTplId);
    const keys = (tpl?.schema||[]).map((f:any)=> f.key).filter((k:string)=> pbCopyFields[k]);
    for (const key of keys){
      try{
        const body:any = { field_key: key, source_kind: ev.source_kind };
        if (ev.source_kind === 'url') body.url = ev.url;
        if (ev.source_kind === 'trade' || ev.source_kind === 'journal') body.source_id = ev.source_id;
        if (ev.note) body.note = ev.note;
        await fetch(`${API_BASE}/playbook-responses/${pbCurrentRespId}/evidence`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(body) });
      }catch{}
    }
    setPbCopySelectEvidenceId(""); setPbCopyFields({});
    await loadEvidence(pbCurrentRespId);
  }

  function renderFieldInput(f:any){
    const v = pbValues[f.key];
    const set = (val:any)=> setPbValues(prev => ({...prev, [f.key]: val}));
    switch(f.type){
      case 'boolean':
        return <input type="checkbox" checked={!!v} onChange={e=>set(e.target.checked)} />;
      case 'number':
        return <input type="number" step="0.01" value={v ?? ''} onChange={e=>set(e.target.value)} />;
      case 'select':
        return <select value={v ?? ''} onChange={e=>set(e.target.value)}>
          <option value="">Select…</option>
          {((f.validation?.options)||[]).map((opt:string)=> <option key={opt} value={opt}>{opt}</option>)}
        </select>;
      case 'rating':
        return <input type="number" min={0} max={5} step={0.5} value={v ?? ''} onChange={e=>set(e.target.value)} />;
      case 'rich_text':
      case 'text':
      default:
        return <input value={v ?? ''} onChange={e=>set(e.target.value)} placeholder={f.label} />;
    }
  }

  async function evaluatePlaybook(){
    if (!pbTplId){ setError('Choose a playbook'); return; }
    try{
      const tpl = pbTemplates.find((t:any)=> t.id===pbTplId);
      const body:any = { template_id: tpl?.id, values: pbValues, template_max_risk_pct: tpl?.template_max_risk_pct, grade_thresholds: tpl?.grade_thresholds, risk_schedule: tpl?.risk_schedule };
      const r = await fetch(`${API_BASE}/playbooks/evaluate`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(body) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Evaluate failed: ${r.status}`);
      setPbEval(j);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function savePlaybook(){
    if (!token || !pbTplId){ setError('Login and choose a playbook'); return; }
    setPbSaving(true);
    try{
      const tpl = pbTemplates.find((t:any)=> t.id===pbTplId);
      const body = { template_id: pbTplId, template_version: tpl?.version, values: pbValues, comments: pbComments };
      const r = await fetch(`${API_BASE}/trades/${params.id}/playbook-responses`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(body) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Save failed: ${r.status}`);
      await loadPlaybookResponses();
      // set current response to the one just saved (may be updated or new)
      const newId = j?.id; if (newId){ setPbCurrentRespId(newId); await loadEvidence(newId); }
      setPbEval(null);
      // Guardrails alert: check for risk cap breach for this trade
      try{
        const day = (data?.close_time_utc || data?.open_time_utc || '').slice(0,10);
        const rb = await fetch(`${API_BASE}/breaches?scope=trade${day?`&start=${day}&end=${day}`:''}`, { headers: token ? { Authorization:`Bearer ${token}` } : undefined });
        if (rb.ok){
          const items = await rb.json();
          const hit = (items||[]).find((b:any)=> b.rule_key==='risk_cap_exceeded' && (b.details?.trade_id === Number(params.id)));
          if (hit){ const d = hit.details || {}; setPbWarn(`Risk cap exceeded: intended ${d.intended}% > cap ${d.cap}% (grade ${d.grade||'?'})`); }
          else setPbWarn(null);
        }
      }catch{}
      try{ (await import('../../../components/Toaster')).toast('Playbook saved','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setPbSaving(false); }
  }

  async function reload(){
    setError(null);
    try{
      const r = await fetch(`${API_BASE}/trades/${params.id}`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || `Failed: ${r.status}`);
      setData(j);
      setNotes(j.notes_md || "");
      setPostNotes(j.post_analysis_md || "");
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function saveNotes(){
    if (!token) { setError('Login required'); return; }
    setSaving(true);
    try{
      const r = await fetch(`${API_BASE}/trades/${params.id}`, { method:'PATCH', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify({ notes_md: notes, post_analysis_md: postNotes })});
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Save failed: ${r.status}`); }
      await reload();
      try{ (await import('../../../components/Toaster')).toast('Notes saved','success'); }catch{}
      setTab('overview');
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setSaving(false); }
  }

  async function createTemplateFromNotes(){
    if (!token){ setError('Login required'); return; }
    const name = prompt('Template name for Trade notes?');
    if (!name) return;
    // Derive sections from headings in notes; fallback to single section
    const lines = (notes||'').split(/\r?\n/);
    const sections: any[] = [];
    let current: { heading: string; placeholder?: string } | null = null;
    let inCode = false;
    for (const ln of lines){
      if (/^```/.test(ln)) { inCode = !inCode; }
      const m = !inCode ? ln.match(/^#{2,}\s+(.+)/) : null;
      if (m){
        if (current){ sections.push({ heading: current.heading, default_included:true, placeholder:(current.placeholder||'').trim() }); }
        current = { heading: m[1].trim(), placeholder: '' };
      } else if (current){
        current.placeholder = (current.placeholder||'') + ln + '\n';
      }
    }
    if (current){ sections.push({ heading: current.heading, default_included:true, placeholder:(current.placeholder||'').trim() }); }
    if (!sections.length){ sections.push({ heading: 'Notes', default_included:true, placeholder: (notes||'').trim() }); }
    try{
      const r = await fetch(`${API_BASE}/templates`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify({ name, target:'trade', sections })});
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Create failed: ${r.status}`);
      await loadTemplates();
      alert('Template created');
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function upload(){
    if (!token || !files || files.length===0){ setError('Choose files'); return; }
    setSaving(true);
    try{
      for (const f of Array.from(files)){
        const fd = new FormData();
        fd.append('file', f);
        if (attMeta.timeframe) fd.append('timeframe', attMeta.timeframe);
        if (attMeta.state) fd.append('state', attMeta.state);
        if (attMeta.view) fd.append('view', attMeta.view);
        if (attMeta.caption) fd.append('caption', attMeta.caption);
        fd.append('reviewed', String(attMeta.reviewed));
        const r = await fetch(`${API_BASE}/trades/${params.id}/attachments`, { method:'POST', headers:{ Authorization:`Bearer ${token}` }, body: fd });
        if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Upload failed: ${r.status}`); }
      }
      setFiles(null);
      setAttMeta({ timeframe:"", state:"", view:"", caption:"", reviewed:false });
      await reload();
      try{ (await import('../../../components/Toaster')).toast('Attachments uploaded','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setSaving(false); }
  }

  async function delAtt(id:number){
    if (!token) return; const ok = confirm('Delete attachment?'); if (!ok) return;
    try{
      const r = await fetch(`${API_BASE}/trades/${params.id}/attachments/${id}`, { method:'DELETE', headers:{ Authorization:`Bearer ${token}` }});
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Delete failed: ${r.status}`); }
      await reload();
      try{ (await import('../../../components/Toaster')).toast('Attachment deleted','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
  }

  function startEdit(a: Attachment){
    setEditMap(m => ({...m, [a.id]: { timeframe:a.timeframe||"", state:a.state||"", view:a.view||"", caption:a.caption||"", reviewed:!!a.reviewed }}));
  }
  function cancelEdit(id:number){ setEditMap(m=> ({...m, [id]: null})); }
  async function saveEdit(a: Attachment){
    if (!token) { setError('Login required'); return; }
    const e = editMap[a.id]; if (!e) return;
    try{
      const r = await fetch(`${API_BASE}/trades/${params.id}/attachments/${a.id}`, { method:'PATCH', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(e) });
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Update failed: ${r.status}`); }
      await reload();
      setEditMap(m=> ({...m, [a.id]: null}));
      try{ (await import('../../../components/Toaster')).toast('Attachment updated','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function deleteSelectedAtts(){
    if (!token){ setError('Login required'); return; }
    if (!data){ setError('No trade loaded'); return; }
    if (!attSel.length){ setError('Select attachments'); return; }
    const ok = confirm(`Delete ${attSel.length} attachment(s)?`); if (!ok) return;
    try{
      const r = await fetch(`${API_BASE}/trades/${params.id}/attachments/batch-delete`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(attSel) });
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Delete failed: ${r.status}`); }
      await reload(); setAttSel([]);
      try{ (await import('../../../components/Toaster')).toast('Deleted selected attachments','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
  }

  function onDragStart(e: React.DragEvent<HTMLDivElement>, id:number){ if (!reorderMode) return; e.dataTransfer.setData('text/plain', String(id)); }
  async function onDrop(e: React.DragEvent<HTMLDivElement>, targetId:number){
    if (!reorderMode || !data) return;
    const src = parseInt(e.dataTransfer.getData('text/plain'),10);
    if (!src || src===targetId) return;
    const order = (data.attachments||[]).map(a=>a.id);
    const from = order.indexOf(src), to = order.indexOf(targetId);
    if (from<0 || to<0) return;
    order.splice(to,0, order.splice(from,1)[0]);
    try{
      const r = await fetch(`${API_BASE}/trades/${params.id}/attachments/reorder`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(order) });
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Reorder failed: ${r.status}`); }
      await reload();
      try{ (await import('../../../components/Toaster')).toast('Reordered attachments','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
  }

  // Return the page directly to avoid any parser quirks around JSX-in-assignment
  return (<main style={{maxWidth: 1000, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>Trade # {params.id}</h1>
      {pbWarn && (
        <div className="notice" style={{margin:'8px 0', padding:'8px 12px', border:'1px solid #fde68a', background:'#fffbeb', color:'#92400e', borderRadius:8}}>
          ⚠︎ {pbWarn}
        </div>
      )}
      {error && <p style={{color:'crimson'}}>{error}</p>}
      {!data ? <p>Loading…</p> : (
        <div>
          <div style={{display:'flex', gap:8, marginBottom:8}}>
            <button onClick={()=>setTab('overview')} disabled={tab==='overview'}>Overview</button>
            <button onClick={()=>setTab('notes')} disabled={tab==='notes'}>Notes</button>
            <button onClick={()=>setTab('attachments')} disabled={tab==='attachments'}>Attachments</button>
            <button onClick={()=>setTab('playbook')} disabled={tab==='playbook'}>Playbook</button>
            <div style={{marginLeft:'auto', display:'flex', gap:8, alignItems:'center'}}>
              <label style={{display:'flex', gap:6, alignItems:'center'}}>
                <input type="checkbox" checked={expIncludePb} onChange={e=>setExpIncludePb(e.target.checked)} /> Include Playbook
              </label>
              <label>Evidence:</label>
              <select value={expEvidence} onChange={e=>setExpEvidence(e.target.value as any)}>
                <option value="links">Links</option>
                <option value="thumbs">Thumbnails</option>
                <option value="full">Full Images</option>
                <option value="none">None</option>
              </select>
              <button onClick={exportMarkdown}>Export MD</button>
              <button onClick={exportPdf}>Export PDF</button>
              <a href="/trades">Back to Trades</a>
            </div>
          </div>

          {tab === 'overview' && (
            <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:8}}>
              <div><b>Account:</b> {data.account_name || '-'}</div>
              <div><b>Symbol:</b> {data.symbol || '-'}</div>
              <div><b>Side:</b> {data.side}</div>
              <div><b>Qty:</b> {data.qty_units ?? '-'}</div>
              <div><b>Entry:</b> {data.entry_price ?? '-'}</div>
              <div><b>Exit:</b> {data.exit_price ?? '-'}</div>
              <div><b>Open:</b> {data.open_time_utc}</div>
              <div><b>Close:</b> {data.close_time_utc ?? '-'}</div>
              <div><b>Net PnL:</b> {data.net_pnl ?? '-'}</div>
              <div><b>Reviewed:</b> {data.reviewed ? 'Yes' : 'No'}</div>
            </div>
          )}

          {tab === 'playbook' && (
            <div>
              <div style={{display:'flex', gap:8, alignItems:'center'}}>
                <label>Playbook:</label>
                <select value={pbTplId} onChange={e=>{ const v = e.target.value ? parseInt(e.target.value,10) : ""; setPbTplId(v); setPbValues({}); setPbComments({}); setPbEval(null); }}>
                  <option value="">Select…</option>
                  {pbTemplates.map((t:any)=> <option key={t.id} value={t.id}>{t.name} (v{t.version})</option>)}
                </select>
                {!!pbTplId && (()=>{
                  const sel = pbTemplates.find((t:any)=> t.id===pbTplId);
                  if (!sel) return null;
                  const latest = pbTemplates.filter((t:any)=> t.name===sel.name).sort((a:any,b:any)=> (b.version||0)-(a.version||0))[0];
                  if (latest && latest.id !== sel.id && latest.version > (sel.version||0)){
                    return <span style={{fontSize:12, color:'#f59e0b'}} title="A newer version of this template exists; switch to use it">
                      Newer version v{latest.version} available. <button onClick={()=>{ setPbTplId(latest.id); setPbValues({}); setPbComments({}); setPbEval(null); }}>Upgrade</button>
                    </span>;
                  }
                  return null;
                })()}
                {pbEval && (
                  <span style={{marginLeft:'auto', fontWeight:600}}>Grade: {pbEval.grade} · Cap: {pbEval.risk_cap_pct}% · Compliance: {(pbEval.compliance_score*100).toFixed(0)}%</span>
                )}
              </div>

              {!!pbTplId && (
                <div style={{marginTop:8, display:'grid', gridTemplateColumns:'1fr', gap:8}}>
                  {pbTemplates.find((t:any)=>t.id===pbTplId)?.schema?.map((f:any)=>(
                    <div key={f.key} style={{display:'grid', gridTemplateColumns:'220px 1fr', gap:8, alignItems:'center'}}>
                      <div style={{fontWeight:600}}>{f.label}{f.required ? ' *' : ''}</div>
                      <div>{renderFieldInput(f)}</div>
                      {f.allow_comment && (
                        <>
                          <div style={{fontSize:12, color:'#64748b'}}>Comment</div>
                          <input value={pbComments[f.key] ?? ''} onChange={e=> setPbComments(prev => ({...prev, [f.key]: e.target.value}))} placeholder="Notes for this criterion" />
                        </>
                      )}
                    </div>
                  ))}
                  <div style={{display:'flex', gap:8}}>
                    <button type="button" onClick={evaluatePlaybook}>Evaluate</button>
                    <button type="button" onClick={savePlaybook} disabled={pbSaving}>{pbSaving ? 'Saving…' : 'Save'}</button>
                  </div>
                </div>
              )}

              {!!pbResponses.length && (
                <div style={{marginTop:16}}>
                  <div style={{display:'flex', alignItems:'center', gap:8, marginBottom:6}}>
                    <div style={{fontWeight:600}}>Previous Responses</div>
                    <select value={pbCurrentRespId ?? ''} onChange={async e=>{ const id = e.target.value ? parseInt(e.target.value,10) : null; setPbCurrentRespId(id); if (id) await loadEvidence(id); }}>
                      <option value="">Select response…</option>
                      {pbResponses.map((r:any)=> (
                        <option key={r.id} value={r.id}>#{r.id} v{r.template_version} — grade {r.computed_grade ?? '—'} — {r.compliance_score != null ? `${Math.round(r.compliance_score*100)}%` : '—'} — {r.created_at}</option>
                      ))}
                    </select>
                  </div>

                  <div style={{marginTop:12, paddingTop:12, borderTop:'1px solid #e5e7eb'}}>
                    <div style={{display:'flex', gap:8, alignItems:'center'}}>
                      <div style={{fontWeight:600}}>Evidence</div>
                      <label style={{marginLeft:12}}>Field:</label>
                      <select value={pbEvidenceField} onChange={e=>setPbEvidenceField(e.target.value)}>
                        <option value="">Select…</option>
                        {pbTemplates.find((t:any)=>t.id===pbTplId)?.schema?.map((f:any)=>(<option key={f.key} value={f.key}>{f.label}</option>))}
                      </select>
                      <span style={{marginLeft:'auto'}}>Current response: {pbCurrentRespId ?? '—'}</span>
                    </div>

                    <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginTop:8}}>
                      <div>
                        <div style={{fontWeight:600, marginBottom:6}}>Link Trade Attachments</div>
                        {!data?.attachments?.length ? <div style={{color:'#64748b'}}>No trade attachments</div> : (
                          <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(140px,1fr))', gap:8}}>
                            {data.attachments.map(a => (
                              <div key={a.id} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:8}}>
                                <div style={{fontSize:12, color:'#334155'}}>{a.filename}</div>
                                <button onClick={()=>addEvidenceTradeAttachment(a.id)}>Link</button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      <div>
                        <div style={{fontWeight:600, marginBottom:6}}>Link Journal Attachments</div>
                        <div style={{display:'flex', gap:6, alignItems:'center', marginBottom:8}}>
                          <input type="date" value={pbJournalDate} onChange={e=>setPbJournalDate(e.target.value)} />
                          <button onClick={loadJournalAttachments} disabled={!pbJournalDate}>Load</button>
                        </div>
                        {!pbJournalAtts.length ? <div style={{color:'#64748b'}}>No journal attachments</div> : (
                          <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(140px,1fr))', gap:8}}>
                            {pbJournalAtts.map(a => (
                              <div key={a.id} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:8}}>
                                <div style={{fontSize:12, color:'#334155'}}>{a.filename}</div>
                                <button onClick={()=>addEvidenceJournalAttachment(a)}>Link</button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    <div style={{marginTop:12}}>
                      <div style={{fontWeight:600, marginBottom:6}}>Link URL Evidence</div>
                      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr auto', gap:8, alignItems:'center'}}>
                        <input placeholder="https://…" value={pbEvidenceUrl} onChange={e=>setPbEvidenceUrl(e.target.value)} />
                        <input placeholder="Note (optional)" value={pbEvidenceNote} onChange={e=>setPbEvidenceNote(e.target.value)} />
                        <button onClick={addEvidenceUrl}>Add URL</button>
                      </div>
                    </div>

                    <div style={{marginTop:12}}>
                      <div style={{fontWeight:600, marginBottom:6}}>Copy Existing Evidence</div>
                      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr auto', gap:8, alignItems:'center'}}>
                        <select value={pbCopySelectEvidenceId ?? ''} onChange={e=> setPbCopySelectEvidenceId(e.target.value ? parseInt(e.target.value,10) : '')}>
                          <option value="">Select evidence…</option>
                          {pbEvidence.map((e:any)=> (
                            <option key={e.id} value={e.id}>#{e.id} {e.field_key} — {e.source_kind}</option>
                          ))}
                        </select>
                        <div style={{display:'flex', flexWrap:'wrap', gap:6}}>
                          {pbTemplates.find((t:any)=>t.id===pbTplId)?.schema?.map((f:any)=> (
                            <label key={f.key} style={{display:'flex', alignItems:'center', gap:4}}>
                              <input type="checkbox" checked={!!pbCopyFields[f.key]} onChange={e=> setPbCopyFields(prev=> ({...prev, [f.key]: e.target.checked}))} />
                              <span style={{fontSize:12}}>{f.label}</span>
                            </label>
                          ))}
                        </div>
                        <button onClick={()=>{ const ev = pbEvidence.find((x:any)=> x.id===pbCopySelectEvidenceId); if (ev) copyEvidenceToFields(ev); }}>Apply</button>
                      </div>
                    </div>

                    <div style={{marginTop:12}}>
                      <div style={{fontWeight:600, marginBottom:6}}>Existing Evidence</div>
                      {!pbEvidence.length ? <div style={{color:'#64748b'}}>No evidence linked</div> : (
                        <ul>
                          {pbEvidence.map((e:any)=>(
                            <li key={e.id} style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                              <span>{e.field_key} — {e.source_kind}{e.url ? `: ${e.url}` : ''}{e.note ? ` — ${e.note}` : ''}</span>
                              <button onClick={()=>removeEvidence(e.id)}>Remove</button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === 'notes' && (
            <div>
              <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8}}>
                <span>Notes (Markdown)</span>
                <button onClick={createTemplateFromNotes}>Create template from these notes</button>
              </div>
              {tpls.length > 0 && (
                <div style={{border:'1px solid #e5e7eb', padding:8, borderRadius:8, marginBottom:8}}>
                  <div style={{display:'flex', gap:8, alignItems:'center', marginBottom:6}}>
                    <label style={{fontWeight:600}}>Apply Template:</label>
                    <select value={tplId} onChange={e=>{
                      const id = parseInt(e.target.value||'0',10); setTplId(id||'');
                      const t = (tpls||[]).find((x:any)=>x.id===id);
                      const map: Record<number, boolean> = {};
                      (t?.sections||[]).forEach((s:any, idx:number)=>{ map[idx] = !!s.default_included; });
                      setTplChecks(map);
                    }}>
                      <option value="">Select…</option>
                      {tpls.map((t:any)=>(<option key={t.id} value={t.id}>{t.name}</option>))}
                    </select>
                    <button disabled={!tplId} onClick={()=>{
                      const t = (tpls||[]).find((x:any)=>x.id===tplId);
                      if (!t) return;
                      const parts: string[] = [];
                      (t.sections||[]).forEach((s:any, idx:number)=>{
                        if (tplChecks[idx]){
                          parts.push(`## ${s.heading}\n\n${s.placeholder||''}\n`);
                        }
                      });
                      const insertStr = (notes ? "\n\n" : "") + parts.join("\n");
                      const ta = notesRef.current;
                      if (ta && typeof ta.selectionStart === 'number' && typeof ta.selectionEnd === 'number'){
                        const start = ta.selectionStart; const end = ta.selectionEnd;
                        setNotes(prev => prev.slice(0, start) + insertStr + prev.slice(end));
                        // restore focus and selection after state update
                        requestAnimationFrame(()=>{
                          try{
                            ta.focus();
                            const pos = start + insertStr.length;
                            ta.setSelectionRange(pos, pos);
                          }catch{}
                        });
                      } else {
                        setNotes(prev => (prev ? prev+"\n\n" : "") + parts.join("\n"));
                      }
                    }}>Insert</button>
                  </div>
                  {!!tplId && (
                    <div style={{display:'flex', flexDirection:'column', gap:4}}>
                      {(tpls.find((x:any)=>x.id===tplId)?.sections||[]).map((s:any, idx:number)=>(
                        <label key={idx} style={{display:'flex', gap:6, alignItems:'center'}}>
                          <input type="checkbox" checked={!!tplChecks[idx]} onChange={e=> setTplChecks(m=>({...m, [idx]: e.target.checked}))} />
                          <span style={{fontWeight:600}}>{s.heading}</span>
                          <span style={{color:'#64748b'}}>{s.placeholder||''}</span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              )}
              <textarea ref={notesRef} rows={8} value={notes} onChange={e=>setNotes(e.target.value)} style={{width:'100%'}} />
              <div style={{margin: '12px 0 8px'}}>Post‑trade Analysis (Markdown):</div>
              <textarea rows={8} value={postNotes} onChange={e=>setPostNotes(e.target.value)} style={{width:'100%'}} />
              <div style={{marginTop:8}}>
                <button onClick={saveNotes} disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
              </div>
            </div>
          )}

          {tab === 'attachments' && (
            <div>
              <div style={{display:'grid', gridTemplateColumns:'repeat(4, minmax(0, 1fr))', gap:8, alignItems:'center'}}>
                <select value={attMeta.timeframe} onChange={e=>setAttMeta(v=>({...v, timeframe:e.target.value}))}>
                  <option value="">Timeframe</option>
                  {["M1","M5","M15","M30","H1","H4","D1"].map(t => (<option key={t} value={t}>{t}</option>))}
                </select>
                <select value={attMeta.state} onChange={e=>setAttMeta(v=>({...v, state:e.target.value}))}>
                  <option value="">State</option>
                  {["marked","unmarked"].map(t => (<option key={t} value={t}>{t}</option>))}
                </select>
                <select value={attMeta.view} onChange={e=>setAttMeta(v=>({...v, view:e.target.value}))}>
                  <option value="">View</option>
                  {["entry","management","exit","post"].map(t => (<option key={t} value={t}>{t}</option>))}
                </select>
                <input placeholder="Caption" value={attMeta.caption} onChange={e=>setAttMeta(v=>({...v, caption:e.target.value}))} />
                <label style={{gridColumn:'1 / span 4'}}>
                  <input type="checkbox" checked={attMeta.reviewed} onChange={e=>setAttMeta(v=>({...v, reviewed:e.target.checked}))} /> Reviewed
                </label>
                <input type="file" multiple onChange={e=>setFiles(e.target.files)} style={{gridColumn:'1 / span 3'}} />
                <button onClick={upload} disabled={saving} style={{gridColumn:'4 / span 1'}}>{saving ? 'Uploading…' : 'Upload'}</button>
              </div>
              <div style={{marginTop:12}}>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8}}>
                  <div style={{display:'flex', alignItems:'center', gap:8}}>
                    <label><input type="checkbox" checked={reorderMode} onChange={e=>setReorderMode(e.target.checked)} /> Reorder</label>
                    {!!attSel.length && <span style={{color:'#64748b'}}>{attSel.length} selected</span>}
                  </div>
                  <div>
                    <button onClick={async ()=>{
                      if (!attSel.length) return;
                      try{
                        const r = await fetch(`${API_BASE}/trades/${params.id}/attachments/zip`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(attSel) });
                        if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Download failed: ${r.status}`); }
                        const blob = await r.blob();
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url; a.download = `trade-${params.id}-attachments.zip`; document.body.appendChild(a); a.click(); a.remove();
                        URL.revokeObjectURL(url);
                      }catch(e:any){ setError(e.message || String(e)); }
                    }} disabled={!attSel.length} style={{marginRight:8}}>Download Selected</button>
                    <button onClick={deleteSelectedAtts} disabled={!attSel.length}>Delete Selected</button>
                  </div>
                </div>
                {!data.attachments.length ? (
                  <p style={{color:'#64748b'}}>No attachments</p>
                ) : (
                  <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(160px, 1fr))', gap:12}}>
                    {data.attachments.map(a => (
                      <div key={a.id} draggable={reorderMode} onDragStart={e=>onDragStart(e, a.id)} onDragOver={e=>{ if (reorderMode) e.preventDefault(); }} onDrop={e=>onDrop(e, a.id)} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:8}}>
                        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:6}}>
                          <input type="checkbox" checked={attSel.includes(a.id)} onChange={e=> setAttSel(prev => e.target.checked ? Array.from(new Set([...prev, a.id])) : prev.filter(x=>x!==a.id)) } />
                          <div style={{display:'flex', gap:8, alignItems:'center'}}>
                            {reorderMode && <span style={{color:'#64748b', fontSize:12, userSelect:'none'}}>Drag to reorder</span>}
                            {!reorderMode && (editMap[a.id] ? (
                              <button onClick={()=>cancelEdit(a.id)}>Cancel</button>
                            ) : (
                              <button onClick={()=>startEdit(a)}>Edit</button>
                            ))}
                          </div>
                        </div>
                        {a.thumb_available && a.thumb_url ? (
                          <a href={`${API_BASE}/trades/${params.id}/attachments/${a.id}/download`} target="_blank" rel="noreferrer">
                            <img src={`${API_BASE}${a.thumb_url}`} alt={a.filename} style={{width:'100%',height:120,objectFit:'cover',borderRadius:6, background:'#f8fafc'}} />
                          </a>
                        ) : (
                          <div style={{height:120,display:'flex',alignItems:'center',justifyContent:'center',background:'#f8fafc',borderRadius:6,color:'#64748b',fontSize:12}}>
                            {a.mime_type?.includes('pdf') ? 'PDF' : 'No preview'}
                          </div>
                        )}
                        <div style={{marginTop:6, fontSize:12, color:'#334155', wordBreak:'break-all'}}>{a.filename}</div>
                        <div style={{color:'#64748b', fontSize:11}}>
                          {a.timeframe || '-'} · {a.state || '-'} · {a.view || '-'} · {a.reviewed ? 'reviewed' : 'unreviewed'}
                        </div>
                        {editMap[a.id] && (
                          <div style={{display:'grid', gridTemplateColumns:'repeat(4, minmax(0, 1fr))', gap:6, marginTop:8, alignItems:'center'}}>
                            <select value={editMap[a.id]!.timeframe} onChange={e=> setEditMap(m=> ({...m, [a.id]: {...(m[a.id]!), timeframe:e.target.value}}))}>
                              <option value="">Timeframe</option>
                              {["M1","M5","M15","M30","H1","H4","D1"].map(t => (<option key={t} value={t}>{t}</option>))}
                            </select>
                            <select value={editMap[a.id]!.state} onChange={e=> setEditMap(m=> ({...m, [a.id]: {...(m[a.id]!), state:e.target.value}}))}>
                              <option value="">State</option>
                              {["marked","unmarked"].map(t => (<option key={t} value={t}>{t}</option>))}
                            </select>
                            <select value={editMap[a.id]!.view} onChange={e=> setEditMap(m=> ({...m, [a.id]: {...(m[a.id]!), view:e.target.value}}))}>
                              <option value="">View</option>
                              {["entry","management","exit","post"].map(t => (<option key={t} value={t}>{t}</option>))}
                            </select>
                            <label>
                              <input type="checkbox" checked={editMap[a.id]!.reviewed} onChange={e=> setEditMap(m=> ({...m, [a.id]: {...(m[a.id]!), reviewed:e.target.checked}}))} /> Reviewed
                            </label>
                            <input placeholder="Caption" value={editMap[a.id]!.caption} onChange={e=> setEditMap(m=> ({...m, [a.id]: {...(m[a.id]!), caption:e.target.value}}))} style={{gridColumn:'1 / span 3'}} />
                            <button onClick={()=>saveEdit(a)} style={{gridColumn:'4 / span 1'}}>Save</button>
                          </div>
                        )}
                        <div style={{display:'flex', gap:8, marginTop:6}}>
                          <a href={`${API_BASE}/trades/${params.id}/attachments/${a.id}/download`} target="_blank" rel="noreferrer">Download</a>
                          <button onClick={()=>delAtt(a.id)}>Delete</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </main>);
}
