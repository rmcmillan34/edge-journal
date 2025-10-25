"use client";
import React, { useEffect, useRef, useState } from "react";

type Journal = { id:number; date:string; title?:string|null; notes_md?:string|null; reviewed:boolean; account_id?:number|null; trade_ids:number[] };
type Trade = { id:number; account_name?:string|null; symbol?:string|null; side:string; qty_units?:number|null; entry_price?:number|null; exit_price?:number|null; open_time_utc:string; close_time_utc?:string|null; net_pnl?:number|null };
type Attachment = { id:number; filename:string; mime_type?:string|null; size_bytes?:number|null; timeframe?:string|null; state?:string|null; view?:string|null; caption?:string|null; reviewed:boolean; thumb_available?:boolean|null; thumb_url?:string|null };

export default function JournalPage({ params }:{ params: { date: string } }){
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const d = params.date; // YYYY-MM-DD
  const [token, setToken] = useState<string>("");
  const [data, setData] = useState<Journal | null>(null);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [atts, setAtts] = useState<Attachment[]>([]);
  const [files, setFiles] = useState<FileList | null>(null);
  const [attMeta, setAttMeta] = useState({ timeframe:"", state:"", view:"", caption:"", reviewed:false });
  const [tpls, setTpls] = useState<any[]>([]);
  const [tplId, setTplId] = useState<number | "">("");
  const [tplChecks, setTplChecks] = useState<Record<number, boolean>>({});
  const notesRef = useRef<HTMLTextAreaElement | null>(null);
  const [attSel, setAttSel] = useState<number[]>([]);
  const [reorderMode, setReorderMode] = useState(false);
  // Instrument checklist (playbook) state
  const [icPurpose, setIcPurpose] = useState<'pre'|'generic'>('pre');
  const [icTemplates, setIcTemplates] = useState<any[]>([]);
  const [icTplId, setIcTplId] = useState<number | "">("");
  const [icSymbol, setIcSymbol] = useState<string>("");
  const [icValues, setIcValues] = useState<Record<string, any>>({});
  const [icComments, setIcComments] = useState<Record<string, string>>({});
  const [icEval, setIcEval] = useState<{ compliance_score:number; grade:string; risk_cap_pct:number }|null>(null);
  const [icResponses, setIcResponses] = useState<any[]>([]);
  const [icCurrentRespId, setIcCurrentRespId] = useState<number | null>(null);
  const [icEvidence, setIcEvidence] = useState<any[]>([]);
  const [icEvidenceField, setIcEvidenceField] = useState<string>("");
  const [icEvidenceUrl, setIcEvidenceUrl] = useState<string>("");
  const [icEvidenceNote, setIcEvidenceNote] = useState<string>("");
  const [icTradeId, setIcTradeId] = useState<number | "">("");
  const [icTradeAtts, setIcTradeAtts] = useState<any[]>([]);
  const [icCopyOpenFor, setIcCopyOpenFor] = useState<number | null>(null);
  const [icCopyFields, setIcCopyFields] = useState<Record<string, boolean>>({});
  const [icCopySelectEvidenceId, setIcCopySelectEvidenceId] = useState<number | "">("");
  const [icWarn, setIcWarn] = useState<string | null>(null);

  useEffect(()=>{ try{ setToken(localStorage.getItem("ej_token") || ""); }catch{} }, []);
  useEffect(()=>{ if (token){ reload(); loadTrades(); loadTemplates(); loadIcTemplates(); } }, [token, d]);
  // Esc exits reorder mode
  useEffect(()=>{
    function onKey(e: KeyboardEvent){ if (e.key === 'Escape' && reorderMode){ e.preventDefault(); setReorderMode(false); } }
    window.addEventListener('keydown', onKey); return ()=> window.removeEventListener('keydown', onKey);
  }, [reorderMode]);

  // Cmd/Ctrl+S to save journal
  useEffect(()=>{
    function onKey(e: KeyboardEvent){
      if ((e.key === 's' || e.key === 'S') && (e.metaKey || e.ctrlKey)){
        e.preventDefault();
        save();
      }
    }
    window.addEventListener('keydown', onKey);
    return ()=> window.removeEventListener('keydown', onKey);
  }, [title, notes, token, d]);

  async function loadTemplates(){
    try{
      const r = await fetch(`${API_BASE}/templates?target=daily`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (r.ok){ const j = await r.json(); setTpls(Array.isArray(j)?j:[]); }
    }catch{}
  }

  async function loadIcTemplates(){
    try{
      const r = await fetch(`${API_BASE}/playbooks/templates?purpose=${icPurpose}`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (r.ok){ const j = await r.json(); setIcTemplates(Array.isArray(j)?j:[]); }
    }catch{}
  }

  async function loadIcExisting(){
    if (!icSymbol) return;
    try{
      const r = await fetch(`${API_BASE}/journal/${d}/instrument/${encodeURIComponent(icSymbol)}/playbook-responses`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (r.ok){ const j = await r.json(); setIcResponses(Array.isArray(j)?j:[]); const latest = (Array.isArray(j) && j.length) ? j[0] : null; if (latest){ setIcCurrentRespId(latest.id); setIcValues(latest.values||{}); setIcComments(latest.comments||{}); await loadIcEvidence(latest.id); } }
    }catch{}
  }

  async function reload(){
    try{
      setError(null);
      const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
      const r = await fetch(`${API_BASE}/journal/${d}`, { headers });
      if (r.status === 404){ setData(null); setTitle(""); setNotes(""); setSelected([]); return; }
      const j = await r.json();
      if (!r.ok) { setError(j.detail || `Failed: ${r.status}`); return; }
      setData(j);
      setTitle(j.title || "");
      setNotes(j.notes_md || "");
      setSelected(j.trade_ids || []);
      await loadAtts(j.id);
    }catch(e:any){
      setError(e?.message || 'Network error');
    }
  }

  async function save(){
    if (!token){ setError('Login required'); return; }
    setSaving(true);
    try{
      const headers:any = { 'Content-Type':'application/json' }; if (token) headers.Authorization = `Bearer ${token}`;
      const r = await fetch(`${API_BASE}/journal/${d}`, { method:'PUT', headers, body: JSON.stringify({ title, notes_md: notes }) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Save failed: ${r.status}`);
      setData(j); setSelected(j.trade_ids || []);
      try{ (await import('../../../components/Toaster')).toast('Journal saved','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setSaving(false); }
  }

  async function icEvaluate(){
    if (!icTplId){ setError('Choose a playbook'); return; }
    try{
      const tpl = icTemplates.find((t:any)=> t.id===icTplId);
      const body:any = { template_id: tpl?.id, values: icValues, template_max_risk_pct: tpl?.template_max_risk_pct, grade_thresholds: tpl?.grade_thresholds, risk_schedule: tpl?.risk_schedule };
      const r = await fetch(`${API_BASE}/playbooks/evaluate`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(body) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Evaluate failed: ${r.status}`);
      setIcEval(j);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function icSave(){
    if (!icTplId || !icSymbol){ setError('Symbol and playbook required'); return; }
    try{
      const tpl = icTemplates.find((t:any)=> t.id===icTplId);
      const body = { template_id: icTplId, template_version: tpl?.version, values: icValues, comments: icComments };
      const r = await fetch(`${API_BASE}/journal/${d}/instrument/${encodeURIComponent(icSymbol)}/playbook-response`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(body) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Save failed: ${r.status}`);
      await loadIcExisting();
      if (j && j.id){ setIcCurrentRespId(j.id); await loadIcEvidence(j.id); }
      // Guardrails alert: fetch day-scope breach for this date/symbol
      try{
        const rb = await fetch(`${API_BASE}/breaches?scope=day&start=${d}&end=${d}`, { headers: token ? { Authorization:`Bearer ${token}` } : undefined });
        if (rb.ok){
          const items = await rb.json();
          const hit = (items||[]).find((b:any)=> b.rule_key==='risk_cap_exceeded' && (b.details?.symbol||'').toUpperCase() === (icSymbol||'').toUpperCase());
          if (hit){ const det = hit.details || {}; setIcWarn(`Risk cap exceeded: intended ${det.intended}% > cap ${det.cap}% (grade ${det.grade||'?'})`); }
          else setIcWarn(null);
        }
      }catch{}
      try{ (await import('../../../components/Toaster')).toast('Instrument checklist saved','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function onPrevChecklistChange(e: React.ChangeEvent<HTMLSelectElement>){
    const val = e.target.value;
    const id = val ? parseInt(val, 10) : null;
    setIcCurrentRespId(id);
    if (id){
      await loadIcEvidence(id);
      const resp = icResponses.find((r:any)=> r.id === id);
      if (resp){
        setIcValues(resp.values || {});
        setIcComments(resp.comments || {});
      }
    }
  }

  async function loadIcEvidence(respId:number){
    try{
      const r = await fetch(`${API_BASE}/playbook-responses/${respId}/evidence`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (r.ok){ const j = await r.json(); setIcEvidence(Array.isArray(j)?j:[]); }
    }catch{}
  }

  async function icAddEvidenceUrl(){
    if (!icCurrentRespId || !icEvidenceField || !icEvidenceUrl){ setError('Select field and enter URL'); return; }
    try{
      const body = { field_key: icEvidenceField, source_kind:'url', url: icEvidenceUrl, note: icEvidenceNote };
      const r = await fetch(`${API_BASE}/playbook-responses/${icCurrentRespId}/evidence`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(body) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Add failed: ${r.status}`);
      setIcEvidenceField(""); setIcEvidenceUrl(""); setIcEvidenceNote("");
      await loadIcEvidence(icCurrentRespId);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function icRemoveEvidence(eid:number){
    if (!icCurrentRespId) return;
    try{
      const r = await fetch(`${API_BASE}/playbook-responses/${icCurrentRespId}/evidence/${eid}`, { method:'DELETE', headers:{ Authorization:`Bearer ${token}` }});
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Delete failed: ${r.status}`); }
      await loadIcEvidence(icCurrentRespId);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function loadIcTradeAttachments(){
    if (!icTradeId) return;
    try{
      const r = await fetch(`${API_BASE}/trades/${icTradeId}/attachments`, { headers: token ? { Authorization:`Bearer ${token}` } : undefined });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Failed: ${r.status}`);
      setIcTradeAtts(Array.isArray(j) ? j : []);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function icAddEvidenceTradeAttachment(att:any){
    if (!icCurrentRespId || !icEvidenceField){ setError('Select field'); return; }
    try{
      const body = { field_key: icEvidenceField, source_kind:'trade', source_id: att.id };
      const r = await fetch(`${API_BASE}/playbook-responses/${icCurrentRespId}/evidence`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(body) });
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Add failed: ${r.status}`); }
      await loadIcEvidence(icCurrentRespId);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function icCopyEvidenceToFields(ev:any){
    if (!icCurrentRespId) return;
    const tpl = icTemplates.find((t:any)=> t.id===icTplId);
    const keys = (tpl?.schema||[]).map((f:any)=> f.key).filter((k:string)=> icCopyFields[k]);
    for (const key of keys){
      try{
        const body:any = { field_key: key, source_kind: ev.source_kind };
        if (ev.source_kind === 'url') body.url = ev.url;
        if (ev.source_kind === 'trade' || ev.source_kind === 'journal') body.source_id = ev.source_id;
        if (ev.note) body.note = ev.note;
        await fetch(`${API_BASE}/playbook-responses/${icCurrentRespId}/evidence`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(body) });
      }catch{}
    }
    setIcCopyOpenFor(null); setIcCopyFields({});
    await loadIcEvidence(icCurrentRespId);
  }

  async function createTemplateFromNotes(){
    if (!token){ setError('Login required'); return; }
    const name = prompt('Template name for Daily notes?');
    if (!name) return;
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
      const r = await fetch(`${API_BASE}/templates`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify({ name, target:'daily', sections })});
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Create failed: ${r.status}`);
      await loadTemplates();
      alert('Template created');
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function deleteJournal(){
    if (!token){ setError('Login required'); return; }
    const ok = confirm('Delete this journal entry? This will remove linked attachments.');
    if (!ok) return;
    try{
      const headers:any = {}; if (token) headers.Authorization = `Bearer ${token}`;
      const r = await fetch(`${API_BASE}/journal/${d}`, { method:'DELETE', headers });
      const j = await r.json().catch(()=>({})); if (!r.ok) throw new Error(j.detail || `Delete failed: ${r.status}`);
      try{ (await import('../../../components/Toaster')).toast('Journal deleted','success'); }catch{}
      window.location.href = '/dashboard';
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function saveLinks(){
    if (!token){ setError('Login required'); return; }
    if (!data){ setError('Create journal first'); return; }
    setSaving(true);
    try{
      const headers:any = { 'Content-Type':'application/json' }; if (token) headers.Authorization = `Bearer ${token}`;
      const r = await fetch(`${API_BASE}/journal/${data.id}/trades`, { method:'POST', headers, body: JSON.stringify(selected) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Link failed: ${r.status}`);
      try{ (await import('../../../components/Toaster')).toast('Linked trades saved','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setSaving(false); }
  }

  async function loadAtts(journalId:number){
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
    const r = await fetch(`${API_BASE}/journal/${journalId}/attachments`, { headers });
    const j = await r.json(); if (!r.ok){ setError(j.detail || `Failed: ${r.status}`); return; }
    setAtts(j || []);
    setAttSel([]);
  }

  async function uploadAtts(){
    if (!token){ setError('Login required'); return; }
    if (!data){ setError('Create journal first'); return; }
    if (!files || files.length===0){ setError('Choose files'); return; }
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
        const r = await fetch(`${API_BASE}/journal/${data.id}/attachments`, { method:'POST', headers:{ Authorization:`Bearer ${token}` }, body: fd });
        if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Upload failed: ${r.status}`); }
      }
      setFiles(null);
      setAttMeta({ timeframe:"", state:"", view:"", caption:"", reviewed:false });
      await loadAtts(data.id);
      try{ (await import('../../../components/Toaster')).toast('Attachments uploaded','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setSaving(false); }
  }

  async function delAtt(id:number){
    if (!token || !data) return; const ok = confirm('Delete attachment?'); if (!ok) return;
    try{
      const r = await fetch(`${API_BASE}/journal/${data.id}/attachments/${id}`, { method:'DELETE', headers:{ Authorization:`Bearer ${token}` }});
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Delete failed: ${r.status}`); }
      await loadAtts(data.id);
      try{ (await import('../../../components/Toaster')).toast('Attachment deleted','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
  }

  const [editMap, setEditMap] = useState<Record<number, {timeframe:string; state:string; view:string; caption:string; reviewed:boolean} | null>>({});
  function startEdit(a: Attachment){
    setEditMap(m => ({...m, [a.id]: { timeframe:a.timeframe||"", state:a.state||"", view:a.view||"", caption:a.caption||"", reviewed:!!a.reviewed }}));
  }
  function cancelEdit(id:number){ setEditMap(m=> ({...m, [id]: null})); }
  async function saveEdit(a: Attachment){
    if (!token || !data){ setError('Login required'); return; }
    const e = editMap[a.id]; if (!e) return;
    try{
      const r = await fetch(`${API_BASE}/journal/${data.id}/attachments/${a.id}`, { method:'PATCH', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(e) });
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Update failed: ${r.status}`); }
      await loadAtts(data.id);
      setEditMap(m=> ({...m, [a.id]: null}));
      try{ (await import('../../../components/Toaster')).toast('Attachment updated','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function deleteSelectedAtts(){
    if (!token || !data){ setError('Login required'); return; }
    if (!attSel.length){ setError('Select attachments'); return; }
    const ok = confirm(`Delete ${attSel.length} attachment(s)?`); if (!ok) return;
    try{
      const r = await fetch(`${API_BASE}/journal/${data.id}/attachments/batch-delete`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(attSel) });
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Delete failed: ${r.status}`); }
      await loadAtts(data.id); setAttSel([]);
      try{ (await import('../../../components/Toaster')).toast('Deleted selected attachments','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
  }

  function onDragStart(e: React.DragEvent<HTMLDivElement>, id:number){ if (!reorderMode) return; e.dataTransfer.setData('text/plain', String(id)); }
  async function onDrop(e: React.DragEvent<HTMLDivElement>, targetId:number){
    if (!reorderMode || !atts.length || !data) return;
    const src = parseInt(e.dataTransfer.getData('text/plain'),10);
    if (!src || src===targetId) return;
    const order = atts.map(a=>a.id);
    const from = order.indexOf(src), to = order.indexOf(targetId);
    if (from<0 || to<0) return;
    order.splice(to,0, order.splice(from,1)[0]);
    try{
      const r = await fetch(`${API_BASE}/journal/${data.id}/attachments/reorder`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(order) });
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Reorder failed: ${r.status}`); }
      await loadAtts(data.id);
      try{ (await import('../../../components/Toaster')).toast('Reordered attachments','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function loadTrades(){
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
    const r = await fetch(`${API_BASE}/trades?start=${d}&end=${d}&limit=200`, { headers });
    const j = await r.json(); if (!r.ok){ setError(j.detail || `Failed: ${r.status}`); return; }
    setTrades(j || []);
  }

  function toggle(id:number, on:boolean){
    setSelected(prev => on ? Array.from(new Set([...prev, id])) : prev.filter(x=>x!==id));
  }

  return (
    <React.Fragment>
    <main style={{maxWidth: 1000, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>Daily Journal — {d}</h1>
      {icWarn && (
        <div className="notice" style={{margin:'8px 0', padding:'8px 12px', border:'1px solid #fde68a', background:'#fffbeb', color:'#92400e', borderRadius:8}}>
          ⚠︎ {icWarn}
        </div>
      )}
      <div style={{marginBottom:8}}><a href="/dashboard">Back to Dashboard</a></div>
      {error && <p style={{color:'crimson'}}>{error}</p>}
      <div style={{display:'grid', gridTemplateColumns:'1fr', gap:8}}>
        {tpls.length > 0 && (
          <div style={{border:'1px solid #e5e7eb', padding:8, borderRadius:8}}>
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
        <input placeholder="Title" value={title} onChange={e=>setTitle(e.target.value)} />
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <span>Notes (Markdown)</span>
          <button onClick={createTemplateFromNotes}>Create template from these notes</button>
        </div>
        <textarea ref={notesRef} rows={10} value={notes} onChange={e=>setNotes(e.target.value)} style={{width:'100%'}} />
        <div style={{marginTop:16, padding:12, border:'1px solid #e5e7eb', borderRadius:8}}>
          <div style={{display:'flex', gap:8, alignItems:'center'}}>
            <h3 style={{margin:0}}>Instrument Checklist</h3>
            <label style={{marginLeft:12}}>Purpose:</label>
            <select value={icPurpose} onChange={e=>{ setIcPurpose((e.target.value as any)); setIcTplId(''); setIcValues({}); setIcComments({}); setIcEval(null); setTimeout(loadIcTemplates, 0); }}>
              <option value="pre">Pre</option>
              <option value="generic">Generic</option>
            </select>
            <label style={{marginLeft:12}}>Symbol:</label>
            <input placeholder="e.g., ESZ5/GBPUSD" value={icSymbol} onChange={e=> setIcSymbol(e.target.value)} onBlur={loadIcExisting} />
            {icEval && (
              <span style={{marginLeft:'auto', fontWeight:600}}>Grade: {icEval.grade} · Cap: {icEval.risk_cap_pct}% · Compliance: {(icEval.compliance_score*100).toFixed(0)}%</span>
            )}
          </div>
          <div style={{display:'flex', gap:8, alignItems:'center', marginTop:8}}>
            <label>Playbook:</label>
            <select value={icTplId} onChange={e=>{ const v = e.target.value ? parseInt(e.target.value,10) : ""; setIcTplId(v); setIcValues({}); setIcComments({}); setIcEval(null); }}>
              <option value="">Select…</option>
              {icTemplates.map((t:any)=> <option key={t.id} value={t.id}>{t.name} (v{t.version})</option>)}
            </select>
            <button onClick={icEvaluate} disabled={!icTplId}>Evaluate</button>
            <button onClick={icSave} disabled={!icTplId || !icSymbol}>Save</button>
          </div>
          {!!icTplId && (
            <div style={{marginTop:8, display:'grid', gridTemplateColumns:'1fr', gap:8}}>
              {icTemplates.find((t:any)=>t.id===icTplId)?.schema?.map((f:any)=> (
                <div key={f.key} style={{display:'grid', gridTemplateColumns:'220px 1fr', gap:8, alignItems:'center'}}>
                  <div style={{fontWeight:600}}>{f.label}{f.required ? ' *' : ''}</div>
                  <FieldInput f={f} v={icValues[f.key]} onChange={(val:any)=> setIcValues(prev=> ({...prev, [f.key]: val}))} />
                  {f.allow_comment && (<>
                    <div style={{fontSize:12, color:'#64748b'}}>Comment</div>
                    <input value={icComments[f.key] ?? ''} onChange={e=> setIcComments(prev => ({...prev, [f.key]: e.target.value}))} placeholder="Notes for this criterion" />
                  </>)}
                </div>
              ))}
            </div>
          )}
          {!!icResponses.length && (
            <div style={{marginTop:16}}>
              <div style={{display:'flex', alignItems:'center', gap:8, marginBottom:6}}>
                <div style={{fontWeight:600}}>Previous Checklists</div>
                <select value={icCurrentRespId ?? ''} onChange={onPrevChecklistChange}>
                  <option value="">Select response…</option>
                  {icResponses.map((r:any)=> (
                    <option key={r.id} value={r.id}>#{r.id} v{r.template_version} — grade {r.computed_grade ?? '—'} — {r.compliance_score != null ? `${Math.round(r.compliance_score*100)}%` : '—'} — {r.created_at}</option>
                  ))}
                </select>
              </div>
              <div style={{marginTop:12, paddingTop:12, borderTop:'1px solid #e5e7eb'}}>
                <div style={{display:'flex', gap:8, alignItems:'center'}}>
                  <div style={{fontWeight:600}}>Evidence</div>
                  <label style={{marginLeft:12}}>Field:</label>
                  <select value={icEvidenceField} onChange={e=>setIcEvidenceField(e.target.value)}>
                    <option value="">Select…</option>
                    {icTemplates.find((t:any)=>t.id===icTplId)?.schema?.map((f:any)=>(<option key={f.key} value={f.key}>{f.label}</option>))}
                  </select>
                  <span style={{marginLeft:'auto'}}>Current response: {icCurrentRespId ?? '—'}</span>
                </div>
                <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginTop:8}}>
                  <div>
                    <div style={{fontWeight:600, marginBottom:6}}>Link Trade Attachments</div>
                    <div style={{display:'flex', gap:6, alignItems:'center', marginBottom:8}}>
                      <select value={icTradeId} onChange={e=> setIcTradeId(e.target.value ? parseInt(e.target.value,10) : '')}>
                        <option value="">Select trade…</option>
                        {(icSymbol ? trades.filter(t => (t.symbol||'').toUpperCase().includes(icSymbol.toUpperCase())) : trades).map(t => (
                          <option key={t.id} value={t.id}>#{t.id} {t.symbol} {t.side} {t.qty_units ?? ''}</option>
                        ))}
                      </select>
                      <button onClick={loadIcTradeAttachments} disabled={!icTradeId}>Load</button>
                    </div>
                    {!icTradeAtts.length ? <div style={{color:'#64748b'}}>No trade attachments</div> : (
                      <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(140px,1fr))', gap:8}}>
                        {icTradeAtts.map(a => (
                          <div key={a.id} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:8}}>
                            <div style={{fontSize:12, color:'#334155'}}>{a.filename}</div>
                            <button onClick={()=>icAddEvidenceTradeAttachment(a)} disabled={!icEvidenceField}>Link to field</button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div>
                    <div style={{fontWeight:600, marginBottom:6}}>Copy Existing Evidence</div>
                    <div style={{display:'grid', gridTemplateColumns:'1fr 1fr auto', gap:8, alignItems:'center'}}>
                      <select value={icCopySelectEvidenceId ?? ''} onChange={e=> setIcCopySelectEvidenceId(e.target.value ? parseInt(e.target.value,10) : '')}>
                        <option value="">Select evidence…</option>
                        {icEvidence.map((e:any)=> (
                          <option key={e.id} value={e.id}>#{e.id} {e.field_key} — {e.source_kind}</option>
                        ))}
                      </select>
                      <div style={{display:'flex', flexWrap:'wrap', gap:6}}>
                        {icTemplates.find((t:any)=>t.id===icTplId)?.schema?.map((f:any)=> (
                          <label key={f.key} style={{display:'flex', alignItems:'center', gap:4}}>
                            <input type="checkbox" checked={!!icCopyFields[f.key]} onChange={e=> setIcCopyFields(prev=> ({...prev, [f.key]: e.target.checked}))} />
                            <span style={{fontSize:12}}>{f.label}</span>
                          </label>
                        ))}
                      </div>
                      <button onClick={()=>{ const ev = icEvidence.find((x:any)=> x.id===icCopySelectEvidenceId); if (ev) icCopyEvidenceToFields(ev); }}>Apply</button>
                    </div>
                  </div>
                </div>
                <div style={{marginTop:8}}>
                  <div style={{fontWeight:600, marginBottom:6}}>Link URL Evidence</div>
                  <div style={{display:'grid', gridTemplateColumns:'1fr 1fr auto', gap:8, alignItems:'center'}}>
                    <input placeholder="https://…" value={icEvidenceUrl} onChange={e=>setIcEvidenceUrl(e.target.value)} />
                    <input placeholder="Note (optional)" value={icEvidenceNote} onChange={e=>setIcEvidenceNote(e.target.value)} />
                    <button onClick={icAddEvidenceUrl}>Add URL</button>
                  </div>
                </div>
                <div style={{marginTop:12}}>
                  <div style={{fontWeight:600, marginBottom:6}}>Existing Evidence</div>
                  {!icEvidence.length ? <div style={{color:'#64748b'}}>No evidence linked</div> : (
                    <ul>
                      {icEvidence.map((e:any)=>(
                        <li key={e.id} style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                          <span>{e.field_key} — {e.source_kind}{e.url ? `: ${e.url}` : ''}{e.note ? ` — ${e.note}` : ''}</span>
                          <button onClick={()=>icRemoveEvidence(e.id)}>Remove</button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
        <div style={{display:'flex', gap:8}}>
          <button onClick={save} disabled={saving}>{saving ? 'Saving…' : (data ? 'Save' : 'Create')}</button>
          {data && (
            <button onClick={deleteJournal} style={{color:'#991b1b'}} disabled={saving}>Delete Journal</button>
          )}
        </div>
      </div>

      <h2 style={{marginTop:16}}>Link Trades for {d}</h2>
      {!trades.length ? <p style={{color:'#64748b'}}>No trades for this day.</p> : (
        <div>
          <ul>
            {trades.map(t => (
              <li key={t.id} style={{display:'flex', alignItems:'center', gap:8}}>
                <input type="checkbox" checked={selected.includes(t.id)} onChange={e=>toggle(t.id, e.target.checked)} />
                <span>#{t.id} {t.symbol} {t.side} {t.qty_units ?? ''} @ {t.entry_price ?? ''}</span>
              </li>
            ))}
          </ul>
          <button onClick={saveLinks} disabled={saving}>Save Links</button>
        </div>
      )}

      <div style={{marginTop:24, color:'#64748b'}}>
        <h2 style={{color:'#334155'}}>Attachments</h2>
        {!data ? (
          <p>Create journal first to add attachments.</p>
        ) : (
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
                {["overview","plan","post"].map(t => (<option key={t} value={t}>{t}</option>))}
              </select>
              <input placeholder="Caption" value={attMeta.caption} onChange={e=>setAttMeta(v=>({...v, caption:e.target.value}))} />
              <label style={{gridColumn:'1 / span 4'}}>
                <input type="checkbox" checked={attMeta.reviewed} onChange={e=>setAttMeta(v=>({...v, reviewed:e.target.checked}))} /> Reviewed
              </label>
              <input type="file" multiple onChange={e=>setFiles(e.target.files)} style={{gridColumn:'1 / span 3'}} />
              <button onClick={uploadAtts} disabled={saving} style={{gridColumn:'4 / span 1'}}>{saving ? 'Uploading…' : 'Upload'}</button>
            </div>
            <div style={{marginTop:12}}>
              <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8}}>
                <div style={{display:'flex', alignItems:'center', gap:8}}>
                  <label><input type="checkbox" checked={reorderMode} onChange={e=>setReorderMode(e.target.checked)} /> Reorder</label>
                  {!!attSel.length && <span style={{color:'#64748b'}}>{attSel.length} selected</span>}
                </div>
                <div>
                  <button onClick={async ()=>{
                    if (!data || !attSel.length) return;
                    try{
                      const r = await fetch(`${API_BASE}/journal/${data.id}/attachments/zip`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(attSel) });
                      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Download failed: ${r.status}`); }
                      const blob = await r.blob();
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url; a.download = `journal-${data.id}-attachments.zip`; document.body.appendChild(a); a.click(); a.remove();
                      URL.revokeObjectURL(url);
                    }catch(e:any){ setError(e.message || String(e)); }
                  }} disabled={!attSel.length} style={{marginRight:8}}>Download Selected</button>
                  <button onClick={deleteSelectedAtts} disabled={!attSel.length}>Delete Selected</button>
                </div>
              </div>
              {!atts.length ? <p style={{color:'#64748b'}}>No attachments</p> : (
                <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(160px, 1fr))', gap:12}}>
                  {atts.map(a => (
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
                        <a href={`${API_BASE}/journal/${data!.id}/attachments/${a.id}/download`} target="_blank" rel="noreferrer">
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
                            {["overview","plan","post"].map(t => (<option key={t} value={t}>{t}</option>))}
                          </select>
                          <label>
                            <input type="checkbox" checked={editMap[a.id]!.reviewed} onChange={e=> setEditMap(m=> ({...m, [a.id]: {...(m[a.id]!), reviewed:e.target.checked}}))} /> Reviewed
                          </label>
                          <input placeholder="Caption" value={editMap[a.id]!.caption} onChange={e=> setEditMap(m=> ({...m, [a.id]: {...(m[a.id]!), caption:e.target.value}}))} style={{gridColumn:'1 / span 3'}} />
                          <button onClick={()=>saveEdit(a)} style={{gridColumn:'4 / span 1'}}>Save</button>
                        </div>
                      )}
                      <div style={{display:'flex', gap:8, marginTop:6}}>
                        <a href={`${API_BASE}/journal/${data!.id}/attachments/${a.id}/download`} target="_blank" rel="noreferrer">Download</a>
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
    </main>
    </React.Fragment>
  );
}

function FieldInput({ f, v, onChange }:{ f:any; v:any; onChange:(val:any)=>void }){
  switch(f.type){
    case 'boolean':
      return <input type="checkbox" checked={!!v} onChange={e=>onChange(e.target.checked)} />;
    case 'number':
      return <input type="number" step="0.01" value={v ?? ''} onChange={e=>onChange(e.target.value)} />;
    case 'select':
      return <select value={v ?? ''} onChange={e=>onChange(e.target.value)}>
        <option value="">Select…</option>
        {((f.validation?.options)||[]).map((opt:string)=> <option key={opt} value={opt}>{opt}</option>)}
      </select>;
    case 'rating':
      return <input type="number" min={0} max={5} step={0.5} value={v ?? ''} onChange={e=>onChange(e.target.value)} />;
    case 'rich_text':
    case 'text':
    default:
      return <input value={v ?? ''} onChange={e=>onChange(e.target.value)} placeholder={f.label} />;
  }
}
