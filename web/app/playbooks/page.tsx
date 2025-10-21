"use client";
import React, { useEffect, useState } from "react";

type PlaybookField = {
  key: string;
  label: string;
  type: 'boolean'|'select'|'number'|'text'|'rating'|'rich_text';
  required?: boolean;
  weight?: number;
  allow_comment?: boolean;
  validation?: Record<string, any>;
};

type PlaybookTemplate = {
  id: number;
  name: string;
  purpose: 'pre'|'in'|'post'|'generic';
  version: number;
  is_active: boolean;
  schema: PlaybookField[];
  grade_thresholds?: Record<string, number>;
  risk_schedule?: Record<string, number>;
  template_max_risk_pct?: number | null;
  created_at?: string;
};

export default function PlaybooksPage(){
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const [token, setToken] = useState("");
  const [purpose, setPurpose] = useState<'pre'|'in'|'post'|'generic'>("post");
  const [items, setItems] = useState<PlaybookTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [quickstart, setQuickstart] = useState<any[]>([]);
  const [editId, setEditId] = useState<number | null>(null);
  const [editName, setEditName] = useState<string>("");
  const [editFields, setEditFields] = useState<PlaybookField[]>([]);
  const [editTemplateMaxRisk, setEditTemplateMaxRisk] = useState<string>("");
  const [editThresholds, setEditThresholds] = useState<Record<string, number>>({ A:0.9, B:0.75, C:0.6 });
  const [editSchedule, setEditSchedule] = useState<Record<string, number>>({ A:1.0, B:0.5, C:0.25, D:0.0 });
  const [editPreviewValues, setEditPreviewValues] = useState<Record<string, any>>({});
  const [editPreviewIntended, setEditPreviewIntended] = useState<string>("");
  const [editPreview, setEditPreview] = useState<{ compliance_score:number; grade:string; risk_cap_pct:number; cap_breakdown:any; exceeded?: boolean; messages?: string[] }|null>(null);
  const [editAdvanced, setEditAdvanced] = useState(false);
  const [editJson, setEditJson] = useState<string>("");
  const [editOriginal, setEditOriginal] = useState<PlaybookTemplate | null>(null);
  const [showDiff, setShowDiff] = useState(false);

  // Create form
  const [name, setName] = useState("");
  const [fields, setFields] = useState<PlaybookField[]>([
    { key: "rule_met", label: "Rule satisfied", type: 'boolean', required: true, weight: 1 }
  ]);
  const [templateMaxRisk, setTemplateMaxRisk] = useState<string>("1.0");
  const [createAdvanced, setCreateAdvanced] = useState(false);
  const [createJson, setCreateJson] = useState<string>("");
  const [previewValues, setPreviewValues] = useState<Record<string, any>>({});
  const [previewIntended, setPreviewIntended] = useState<string>("");
  const [preview, setPreview] = useState<{ compliance_score:number; grade:string; risk_cap_pct:number; cap_breakdown:any; exceeded?: boolean; messages?: string[] }|null>(null);

  useEffect(()=>{ try{ setToken(localStorage.getItem("ej_token") || ""); }catch{} },[]);
  useEffect(()=>{ if (token){ load(); } }, [token, purpose]);
  useEffect(()=>{ if (token){ loadQuickstart(); } }, [token]);

  async function load(){
    setError(null); setLoading(true);
    try{
      const url = `${API_BASE}/playbooks/templates?purpose=${purpose}`;
      const r = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Failed: ${r.status}`);
      setItems(Array.isArray(j) ? j : []);
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setLoading(false); }
  }

  async function loadQuickstart(){
    try{
      const r = await fetch(`${API_BASE}/playbooks/templates/quickstart`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Failed: ${r.status}`);
      setQuickstart(Array.isArray(j.items)?j.items:[]);
    }catch{}
  }

  function updateField(idx:number, patch: Partial<PlaybookField>){
    setFields(prev => prev.map((f,i)=> i===idx ? { ...f, ...patch } : f));
  }
  function addField(){ setFields(prev => [...prev, { key:"", label:"", type:'boolean', required:false, weight:1 }]); }
  function removeField(idx:number){ setFields(prev => prev.filter((_,i)=> i!==idx)); }
  function moveField(idx:number, dir:-1|1){
    setFields(prev => {
      const arr = prev.slice();
      const j = idx + dir;
      if (j<0 || j>=arr.length) return arr;
      const [it] = arr.splice(idx,1);
      arr.splice(j,0,it);
      return arr;
    });
  }
  function onDragStartNew(e: React.DragEvent<HTMLDivElement>, idx:number){ e.dataTransfer.setData('text/plain', String(idx)); }
  function onDragOverNew(e: React.DragEvent<HTMLDivElement>){ e.preventDefault(); }
  function onDropNew(e: React.DragEvent<HTMLDivElement>, idx:number){
    e.preventDefault();
    const s = e.dataTransfer.getData('text/plain');
    const from = parseInt(s,10); if (isNaN(from)) return;
    setFields(prev => {
      const arr = prev.slice();
      const [it] = arr.splice(from,1);
      arr.splice(idx,0,it);
      return arr;
    });
  }

  async function createTemplate(){
    if (!token){ setError('Login required'); return; }
    if (!name.trim()){ setError('Name is required'); return; }
    const schema = fields.filter(f => f.key && f.label);
    if (!schema.length){ setError('Add at least one field'); return; }
    const body = {
      name: name.trim(),
      purpose,
      schema,
      template_max_risk_pct: parseFloat(templateMaxRisk || '0') || 0,
      grade_thresholds: { A:0.9, B:0.75, C:0.6 },
      risk_schedule: { A:1.0, B:0.5, C:0.25, D:0.0 },
    };
    try{
      const r = await fetch(`${API_BASE}/playbooks/templates`, {
        method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` },
        body: JSON.stringify(body)
      });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Create failed: ${r.status}`);
      setName(""); setFields([{ key:"rule_met", label:"Rule satisfied", type:'boolean', required:true, weight:1 }]); setTemplateMaxRisk("1.0");
      await load();
    }catch(e:any){ setError(e.message || String(e)); }
  }

  function renderPreviewInput(f: PlaybookField){
    const v = previewValues[f.key];
    const set = (val:any)=> setPreviewValues(prev => ({...prev, [f.key]: val}));
    switch(f.type){
      case 'boolean':
        return <input type="checkbox" checked={!!v} onChange={e=>set(e.target.checked)} />;
      case 'number':
        return <input type="number" step="0.01" value={v ?? ''} onChange={e=>set(e.target.value)} />;
      case 'select':
        return <select value={v ?? ''} onChange={e=>set(e.target.value)}>
          <option value="">Select…</option>
          {((f.validation?.options)||[]).map((opt:any)=> <option key={opt} value={opt}>{opt}</option>)}
        </select>;
      case 'rating':
        return <input type="number" step="0.5" min={0} max={5} value={v ?? ''} onChange={e=>set(e.target.value)} />;
      case 'rich_text':
      case 'text':
      default:
        return <input value={v ?? ''} onChange={e=>set(e.target.value)} />;
    }
  }

  async function runPreview(){
    setError(null);
    try{
      const body:any = { schema: fields, values: previewValues, template_max_risk_pct: parseFloat(templateMaxRisk||'0') };
      if (previewIntended) body.intended_risk_pct = parseFloat(previewIntended);
      const r = await fetch(`${API_BASE}/playbooks/evaluate`, { method:'POST', headers: { 'Content-Type':'application/json', ...(token ? { Authorization:`Bearer ${token}` } : {}) }, body: JSON.stringify(body) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Preview failed: ${r.status}`);
      setPreview(j);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function archiveTemplate(id:number){
    if (!token) return;
    setBusyId(id);
    try{
      const r = await fetch(`${API_BASE}/playbooks/templates/${id}`, { method:'DELETE', headers:{ Authorization:`Bearer ${token}` }});
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Archive failed: ${r.status}`);
      await load();
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setBusyId(null); }
  }

  async function cloneTemplate(t: PlaybookTemplate){
    if (!token) return;
    setBusyId(t.id);
    try{
      const body = { name: `${t.name} (Copy)` };
      const r = await fetch(`${API_BASE}/playbooks/templates/${t.id}/clone`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(body) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Clone failed: ${r.status}`);
      await load();
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setBusyId(null); }
  }

  async function exportTemplate(t: PlaybookTemplate){
    if (!token) return;
    setBusyId(t.id);
    try{
      const r = await fetch(`${API_BASE}/playbooks/templates/${t.id}/export`, { method:'POST', headers:{ Authorization:`Bearer ${token}` }});
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Export failed: ${r.status}`);
      const blob = new Blob([JSON.stringify(j, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `${t.name.replace(/\s+/g,'_')}_v${t.version}.playbook.json`; a.click(); setTimeout(()=>URL.revokeObjectURL(url), 5000);
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setBusyId(null); }
  }

  const [importText, setImportText] = useState("");
  async function importTemplate(){
    if (!token) return;
    try{
      const payload = JSON.parse(importText);
      const r = await fetch(`${API_BASE}/playbooks/templates/import`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(payload) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Import failed: ${r.status}`);
      setImportText(""); await load();
    }catch(e:any){ setError(e.message || String(e)); }
  }

  function startEdit(t: PlaybookTemplate){
    setEditId(t.id);
    setEditName(t.name);
    setEditFields(JSON.parse(JSON.stringify(t.schema||[])));
    setEditTemplateMaxRisk((t.template_max_risk_pct ?? '').toString());
    setEditThresholds(t.grade_thresholds || { A:0.9, B:0.75, C:0.6 });
    setEditSchedule(t.risk_schedule || { A:1.0, B:0.5, C:0.25, D:0.0 });
    setEditOriginal(t);
    setEditAdvanced(false); setEditJson(""); setShowDiff(false);
  }

  function updateEditField(idx:number, patch: Partial<PlaybookField>){
    setEditFields(prev => prev.map((f,i)=> i===idx ? { ...f, ...patch } : f));
  }
  function addEditField(){ setEditFields(prev => [...prev, { key:"", label:"", type:'boolean', required:false, weight:1 }]); }
  function removeEditField(idx:number){ setEditFields(prev => prev.filter((_,i)=> i!==idx)); }
  function moveEditField(idx:number, dir:-1|1){
    setEditFields(prev => {
      const arr = prev.slice();
      const j = idx + dir;
      if (j<0 || j>=arr.length) return arr;
      const [it] = arr.splice(idx,1);
      arr.splice(j,0,it);
      return arr;
    });
  }

  function validateEdit(): string | null{
    const keys = new Set<string>();
    for (const f of editFields){
      const k = (f.key||'').trim().toLowerCase();
      if (!k) return 'Each field must have a non-empty key.';
      if (keys.has(k)) return `Duplicate key: ${f.key}`;
      keys.add(k);
    }
    if (!editName.trim()) return 'Name is required.';
    return null;
  }

  async function saveEdit(){
    const err = validateEdit(); if (err){ setError(err); return; }
    if (!editId || !token) return;
    try{
      const body:any = {
        name: editName.trim(),
        schema: editFields,
        grade_thresholds: editThresholds,
        risk_schedule: editSchedule,
        template_max_risk_pct: editTemplateMaxRisk ? parseFloat(editTemplateMaxRisk) : null,
      };
      const r = await fetch(`${API_BASE}/playbooks/templates/${editId}`, { method:'PATCH', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(body) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Update failed: ${r.status}`);
      setEditId(null);
      await load();
    }catch(e:any){ setError(e.message || String(e)); }
  }

  function renderEditFieldRow(f: PlaybookField, idx:number){
    return (
      <div key={idx} draggable onDragStart={e=>{ e.dataTransfer.setData('text/plain', String(idx)); }} onDragOver={e=>e.preventDefault()} onDrop={e=>{ e.preventDefault(); const s = e.dataTransfer.getData('text/plain'); const from = parseInt(s,10); if (isNaN(from)) return; moveEditFieldTo(from, idx); }} style={{display:'grid', gridTemplateColumns:'1fr 120px 80px 80px 1fr auto auto', gap:8, alignItems:'center'}}>
        <input placeholder="Key" value={f.key} onChange={e=>updateEditField(idx,{ key: e.target.value })} />
        <select value={f.type} onChange={e=>updateEditField(idx,{ type: (e.target.value as any) })}>
          <option value="boolean">Boolean</option>
          <option value="select">Select</option>
          <option value="number">Number</option>
          <option value="text">Text</option>
          <option value="rating">Rating</option>
          <option value="rich_text">Rich Text</option>
        </select>
        <label style={{display:'flex', alignItems:'center', gap:6}}>
          <input type="checkbox" checked={!!f.required} onChange={e=>updateEditField(idx,{ required:e.target.checked })} /> req
        </label>
        <input type="number" step="0.1" value={f.weight ?? 1} onChange={e=>updateEditField(idx,{ weight: parseFloat(e.target.value) })} />
        <div style={{display:'grid', gridTemplateColumns:'1fr', gap:6}}>
          {f.type==='number' && (
            <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:6}}>
              <input placeholder="min" type="number" value={f.validation?.min ?? ''} onChange={e=>updateEditField(idx,{ validation: { ...(f.validation||{}), min: e.target.value === '' ? undefined : parseFloat(e.target.value) } })} />
              <input placeholder="max" type="number" value={f.validation?.max ?? ''} onChange={e=>updateEditField(idx,{ validation: { ...(f.validation||{}), max: e.target.value === '' ? undefined : parseFloat(e.target.value) } })} />
            </div>
          )}
          {f.type==='select' && (
            <input placeholder="options (comma-separated)" value={Array.isArray(f.validation?.options)? (f.validation!.options as any[]).join(',') : ''} onChange={e=>updateEditField(idx,{ validation: { ...(f.validation||{}), options: e.target.value.split(',').map(s=>s.trim()).filter(Boolean) } })} />
          )}
          <label style={{display:'flex', alignItems:'center', gap:6}}>
            <input type="checkbox" checked={!!f.allow_comment} onChange={e=>updateEditField(idx,{ allow_comment:e.target.checked })} /> allow comment
          </label>
        </div>
        <div style={{display:'flex', gap:6}}>
          <button onClick={()=>moveEditField(idx,-1)} disabled={idx===0}>↑</button>
          <button onClick={()=>moveEditField(idx,1)} disabled={idx===editFields.length-1}>↓</button>
        </div>
        <button onClick={()=>removeEditField(idx)}>Remove</button>
      </div>
    );
  }

  function moveEditFieldTo(from:number, to:number){
    setEditFields(prev => {
      const arr = prev.slice();
      if (from<0 || from>=arr.length || to<0 || to>=arr.length) return arr;
      const [it] = arr.splice(from,1);
      arr.splice(to,0,it);
      return arr;
    });
  }

  async function runEditPreview(){
    setError(null);
    try{
      const body:any = { schema: editFields, values: editPreviewValues, template_max_risk_pct: editTemplateMaxRisk? parseFloat(editTemplateMaxRisk) : undefined, grade_thresholds: editThresholds, risk_schedule: editSchedule };
      if (editPreviewIntended) body.intended_risk_pct = parseFloat(editPreviewIntended);
      const r = await fetch(`${API_BASE}/playbooks/evaluate`, { method:'POST', headers: { 'Content-Type':'application/json', ...(token ? { Authorization:`Bearer ${token}` } : {}) }, body: JSON.stringify(body) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Preview failed: ${r.status}`);
      setEditPreview(j);
    }catch(e:any){ setError(e.message || String(e)); }
  }

  return (
    <main style={{maxWidth: 1000, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>Playbooks</h1>
      <div style={{marginBottom:8, overflowX:'auto'}}>
        <a href="/dashboard">Back to Dashboard</a>
      </div>
      {error && <p style={{color:'crimson'}}>{error}</p>}

      <div style={{display:'flex', gap:12, alignItems:'center', margin:'8px 0', overflowX:'auto'}}>
        <label>Purpose:</label>
        <select value={purpose} onChange={e=> setPurpose((e.target.value as any))}>
          <option value="pre">Pre</option>
          <option value="in">In</option>
          <option value="post">Post</option>
          <option value="generic">Generic</option>
        </select>
        <a href="/trades" style={{marginLeft:'auto'}}>Go to Trades</a>
      </div>

      <section style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12, margin:'12px 0', overflowX:'auto'}}>
        <h2 style={{marginTop:0}}>Create Playbook</h2>
        <div style={{display:'grid', gridTemplateColumns:'1fr', gap:8}}>
          <input placeholder="Name" value={name} onChange={e=>setName(e.target.value)} />
          <div style={{display:'flex', gap:8, alignItems:'center'}}>
            <button type="button" onClick={()=>{
              setCreateAdvanced(v=>!v);
              if (!createAdvanced){
                const payload = { schema: fields, template_max_risk_pct: parseFloat(templateMaxRisk||'0')||0, grade_thresholds: { A:0.9, B:0.75, C:0.6 }, risk_schedule: { A:1.0, B:0.5, C:0.25, D:0.0 } };
                setCreateJson(JSON.stringify(payload, null, 2));
              }
            }}>{createAdvanced ? 'Simple Editor' : 'Advanced JSON'}</button>
            {createAdvanced && <button type="button" onClick={()=>{
              try{
                const j = JSON.parse(createJson);
                if (Array.isArray(j.schema)){ setFields(j.schema); }
                if (j.template_max_risk_pct != null){ setTemplateMaxRisk(String(j.template_max_risk_pct)); }
                setError(null);
              }catch(e:any){ setError('Invalid JSON: '+(e.message||e)); }
            }}>Apply JSON</button>}
          </div>
          {createAdvanced && (
            <textarea rows={12} style={{width:'100%'}} value={createJson} onChange={e=>setCreateJson(e.target.value)} />
          )}
          <div style={{display:'grid', gridTemplateColumns:'minmax(0,1fr) minmax(0,1fr) 120px 100px 120px auto auto', gap:8, alignItems:'center'}}>
            <div style={{fontWeight:600}}>Key</div>
            <div style={{fontWeight:600}}>Label</div>
            <div>Type</div>
            <div>Required</div>
            <div>Weight</div>
            <div>Reorder</div>
            <div></div>
          </div>
          {(fields||[]).map((f, idx) => (
            <div key={idx} draggable onDragStart={e=>onDragStartNew(e, idx)} onDragOver={onDragOverNew} onDrop={e=>onDropNew(e, idx)} style={{display:'grid', gridTemplateColumns:'minmax(0,1fr) minmax(0,1fr) 120px 100px 120px auto auto', gap:8, alignItems:'center'}}>
              <input placeholder="Key" value={f.key} onChange={e=>updateField(idx,{ key:e.target.value })} />
              <input placeholder="Label" value={f.label} onChange={e=>updateField(idx,{ label:e.target.value })} />
              <select value={f.type} onChange={e=>updateField(idx,{ type: (e.target.value as any) })}>
                <option value="boolean">Boolean</option>
                <option value="select">Select</option>
                <option value="number">Number</option>
                <option value="text">Text</option>
                <option value="rating">Rating</option>
                <option value="rich_text">Rich Text</option>
              </select>
              <label style={{display:'flex', alignItems:'center', gap:6}}>
                <input type="checkbox" checked={!!f.required} onChange={e=>updateField(idx,{ required:e.target.checked })} /> Required
              </label>
              <input type="number" step="0.1" value={f.weight ?? 1} onChange={e=>updateField(idx,{ weight: parseFloat(e.target.value) })} />
              <div style={{display:'flex', gap:6}}>
                <button onClick={()=>moveField(idx,-1)} disabled={idx===0}>↑</button>
                <button onClick={()=>moveField(idx,1)} disabled={idx===fields.length-1}>↓</button>
              </div>
              <button onClick={()=>removeField(idx)}>Remove</button>
            </div>
          ))}
          <button onClick={addField}>Add Field</button>
          <div style={{display:'flex', gap:12, alignItems:'center'}}>
            <label>Template Max Risk %</label>
            <input type="number" step="0.05" value={templateMaxRisk} onChange={e=>setTemplateMaxRisk(e.target.value)} />
          </div>
          <div>
            <button onClick={createTemplate} disabled={loading}>{loading ? 'Working…' : 'Create'}</button>
          </div>
          <div style={{marginTop:16, borderTop:'1px solid #e5e7eb', paddingTop:12}}>
            <h3 style={{marginTop:0}}>Live Evaluation Preview</h3>
            <div style={{display:'grid', gridTemplateColumns:'1fr', gap:8}}>
              {(fields||[]).map((f, idx) => (
                <div key={idx} style={{display:'grid', gridTemplateColumns:'180px minmax(0,1fr)', gap:8, alignItems:'center'}}>
                  <div style={{fontWeight:600}}>{f.label || f.key}{f.required ? ' *' : ''}</div>
                  <div>{renderPreviewInput(f)}</div>
                </div>
              ))}
              <div style={{display:'flex', gap:12, alignItems:'center'}}>
                <label>Intended Risk %</label>
                <input type="number" step="0.05" value={previewIntended} onChange={e=>setPreviewIntended(e.target.value)} />
                <button onClick={runPreview}>Preview</button>
              </div>
              {preview && (
                <div style={{display:'flex', gap:12, alignItems:'center', color: preview.exceeded ? 'crimson' : 'inherit'}}>
                  <div><b>Grade:</b> {preview.grade}</div>
                  <div><b>Compliance:</b> {Math.round(preview.compliance_score * 100)}%</div>
                  <div><b>Risk Cap:</b> {preview.risk_cap_pct}%</div>
                  {!!preview.messages?.length && <div title={preview.messages.join('\n')}>⚠︎</div>}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <section style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12, overflowX:'auto'}}>
        <h2 style={{marginTop:0}} title="Templates you’ve created (filtered by purpose)">Your Playbooks ({purpose})</h2>
        {loading ? <p>Loading…</p> : (!items.length ? <p style={{color:'#64748b'}}>No playbooks yet</p> : (
          <div style={{display:'flex', flexDirection:'column', gap:12}}>
            {items.map((t) => (
              <div key={t.id} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12}}>
                <div style={{display:'flex', gap:8, alignItems:'center'}}>
                  <div style={{fontWeight:600}}>{t.name}</div>
                  <span style={{fontSize:12, color:'#64748b'}}>v{t.version}</span>
                  <span style={{fontSize:12, color:'#64748b', marginLeft:'auto'}}>#{t.id}</span>
                </div>
                <div style={{marginTop:6, fontSize:13, color:'#475569'}}>Fields: {t.schema.length}; Max Risk: {t.template_max_risk_pct ?? '—'}%</div>
                <div style={{display:'flex', gap:8, marginTop:8}}>
                  <button onClick={()=>startEdit(t)} disabled={busyId===t.id || editId===t.id}>Edit</button>
                  <button onClick={()=>cloneTemplate(t)} disabled={busyId===t.id}>Clone</button>
                  <button onClick={()=>exportTemplate(t)} disabled={busyId===t.id}>Export</button>
                  <button onClick={()=>archiveTemplate(t.id)} disabled={busyId===t.id || !t.is_active}>{t.is_active ? 'Archive' : 'Archived'}</button>
                </div>
                {editId===t.id && (
                  <div style={{marginTop:12, paddingTop:12, borderTop:'1px solid #e5e7eb'}}>
                    <div style={{display:'flex', gap:8, alignItems:'center', marginBottom:6}}>
                      <button type="button" onClick={()=>{
                        setEditAdvanced(v=>!v);
                        if (!editAdvanced){
                          const payload = { name: editName, schema: editFields, template_max_risk_pct: editTemplateMaxRisk? parseFloat(editTemplateMaxRisk): null, grade_thresholds: editThresholds, risk_schedule: editSchedule };
                          setEditJson(JSON.stringify(payload, null, 2));
                        }
                      }}>{editAdvanced ? 'Simple Editor' : 'Advanced JSON'}</button>
                      {editAdvanced && <button type="button" onClick={()=>{
                        try{
                          const j = JSON.parse(editJson);
                          if (typeof j.name === 'string') setEditName(j.name);
                          if (Array.isArray(j.schema)) setEditFields(j.schema);
                          if (j.template_max_risk_pct != null) setEditTemplateMaxRisk(String(j.template_max_risk_pct));
                          if (j.grade_thresholds) setEditThresholds(j.grade_thresholds);
                          if (j.risk_schedule) setEditSchedule(j.risk_schedule);
                          setError(null);
                        }catch(e:any){ setError('Invalid JSON: '+(e.message||e)); }
                      }}>Apply JSON</button>}
                    </div>
                    {editAdvanced && (
                      <textarea rows={12} style={{width:'100%'}} value={editJson} onChange={e=>setEditJson(e.target.value)} />
                    )}
                    <div style={{display:'grid', gridTemplateColumns:'minmax(0, 420px) auto', gap:8}}>
                      <input style={{width:'100%', maxWidth:420}} placeholder="Template name" value={editName} onChange={e=>setEditName(e.target.value)} />
                      <div style={{display:'flex', gap:6, alignItems:'center', justifyContent:'flex-end'}}>
                        <label style={{whiteSpace:'nowrap'}}>Max %</label>
                        <input style={{width:80}} type="number" step="0.05" value={editTemplateMaxRisk} onChange={e=>setEditTemplateMaxRisk(e.target.value)} />
                      </div>
                    </div>
                    <div style={{marginTop:8}}>
                      <div style={{fontWeight:600, marginBottom:6}}>Fields</div>
                      <div style={{display:'grid', gridTemplateColumns:'minmax(0,1fr) 120px 80px 80px minmax(0,1fr) auto auto', gap:8, alignItems:'center', marginBottom:6}}>
                        <div>Key</div>
                        <div>Type</div>
                        <div>Req</div>
                        <div>Weight</div>
                        <div>Validation/Options</div>
                        <div>Reorder</div>
                        <div></div>
                      </div>
                      {editFields.map((f, idx)=> renderEditFieldRow(f, idx))}
                      <button onClick={addEditField} style={{marginTop:8}}>Add Field</button>
                    </div>
                    <div style={{marginTop:12, display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(260px, 1fr))', gap:12}}>
                      <div>
                        <div style={{fontWeight:600, marginBottom:6}}>Grade Thresholds</div>
                        <div style={{display:'grid', gridTemplateColumns:'repeat(3, minmax(0, 1fr))', gap:6}}>
                          {['A','B','C'].map(k => (
                            <div key={k} style={{display:'flex', alignItems:'center', gap:6}}>
                              <label style={{width:18}}>{k}</label>
                              <input style={{width:'100%'}} type="number" step="0.01" value={editThresholds[k] ?? ''} onChange={e=> setEditThresholds(prev=> ({...prev, [k]: e.target.value===''? undefined as any : parseFloat(e.target.value)}))} />
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <div style={{fontWeight:600, marginBottom:6}}>Risk Schedule</div>
                        <div style={{display:'grid', gridTemplateColumns:'repeat(4, minmax(0, 1fr))', gap:6}}>
                          {['A','B','C','D'].map(k => (
                            <div key={k} style={{display:'flex', alignItems:'center', gap:6}}>
                              <label style={{width:18}}>{k}</label>
                              <input style={{width:'100%'}} type="number" step="0.05" value={editSchedule[k] ?? ''} onChange={e=> setEditSchedule(prev=> ({...prev, [k]: e.target.value===''? undefined as any : parseFloat(e.target.value)}))} />
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                    {showDiff && editOriginal && (
                      <div style={{marginTop:12, borderTop:'1px solid #e5e7eb', paddingTop:12}}>
                        <div style={{fontWeight:600, marginBottom:6}}>Review Changes</div>
                        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12}}>
                          <div>
                            <div style={{fontSize:12, color:'#64748b'}}>Original</div>
                            <pre style={{whiteSpace:'pre-wrap', background:'#0f172a', color:'#e2e8f0', padding:8, borderRadius:6}}>{JSON.stringify({ name: editOriginal.name, schema: editOriginal.schema, template_max_risk_pct: editOriginal.template_max_risk_pct, grade_thresholds: editOriginal.grade_thresholds, risk_schedule: editOriginal.risk_schedule }, null, 2)}</pre>
                          </div>
                          <div>
                            <div style={{fontSize:12, color:'#64748b'}}>Proposed</div>
                            <pre style={{whiteSpace:'pre-wrap', background:'#0f172a', color:'#e2e8f0', padding:8, borderRadius:6}}>{JSON.stringify({ name: editName, schema: editFields, template_max_risk_pct: editTemplateMaxRisk? parseFloat(editTemplateMaxRisk): null, grade_thresholds: editThresholds, risk_schedule: editSchedule }, null, 2)}</pre>
                          </div>
                        </div>
                      </div>
                    )}
                    <div style={{marginTop:12, borderTop:'1px solid #e5e7eb', paddingTop:12}}>
                      <div style={{display:'flex', alignItems:'center', gap:8, marginBottom:6}}>
                        <div style={{fontWeight:600}}>In-Editor Preview</div>
                        <div style={{marginLeft:'auto', display:'flex', alignItems:'center', gap:8}}>
                          <label>Intended Risk %</label>
                          <input type="number" step="0.05" value={editPreviewIntended} onChange={e=>setEditPreviewIntended(e.target.value)} />
                          <button onClick={runEditPreview}>Preview</button>
                        </div>
                      </div>
                      <div style={{display:'grid', gridTemplateColumns:'1fr', gap:8}}>
                        {editFields.map((f, idx)=> (
                          <div key={idx} style={{display:'grid', gridTemplateColumns:'180px minmax(0,1fr)', gap:8, alignItems:'center'}}>
                            <div style={{fontWeight:600}}>{f.label || f.key}{f.required ? ' *' : ''}</div>
                            <div>{(() => {
                              const v = editPreviewValues[f.key];
                              const set = (val:any)=> setEditPreviewValues(prev => ({...prev, [f.key]: val}));
                              switch(f.type){
                                case 'boolean': return <input type="checkbox" checked={!!v} onChange={e=>set(e.target.checked)} />;
                                case 'number': return <input type="number" step="0.01" value={v ?? ''} onChange={e=>set(e.target.value)} />;
                                case 'select': return <select value={v ?? ''} onChange={e=>set(e.target.value)}><option value="">Select…</option>{((f.validation?.options)||[]).map((opt:any)=> <option key={opt} value={opt}>{opt}</option>)}</select>;
                                case 'rating': return <input type="number" step="0.5" min={0} max={5} value={v ?? ''} onChange={e=>set(e.target.value)} />;
                                case 'rich_text':
                                case 'text':
                                default: return <input value={v ?? ''} onChange={e=>set(e.target.value)} />;
                              }
                            })()}</div>
                          </div>
                        ))}
                        {editPreview && (
                          <div style={{display:'flex', gap:12, alignItems:'center', color: editPreview.exceeded ? 'crimson' : 'inherit'}}>
                            <div><b>Grade:</b> {editPreview.grade}</div>
                            <div><b>Compliance:</b> {Math.round(editPreview.compliance_score * 100)}%</div>
                            <div><b>Risk Cap:</b> {editPreview.risk_cap_pct}%</div>
                            {!!editPreview.messages?.length && <div title={editPreview.messages.join('\n')}>⚠︎</div>}
                          </div>
                        )}
                      </div>
                    </div>
                    <div style={{marginTop:12, display:'flex', gap:8}}>
                      {!showDiff ? (
                        <button onClick={()=>setShowDiff(true)}>Review Changes</button>
                      ) : (
                        <button onClick={saveEdit}>Confirm Save (new version)</button>
                      )}
                      <button onClick={()=>setEditId(null)}>Cancel</button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
      </section>

      <section style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12, marginTop:12}}>
        <h2 style={{marginTop:0}}>Import Playbook</h2>
        <p style={{color:'#64748b', marginTop:0}}>Paste JSON exported from the Playbooks API.</p>
        <textarea placeholder="Paste exported Playbook JSON here" value={importText} onChange={e=>setImportText(e.target.value)} rows={10} style={{width:'100%'}} />
        <div style={{marginTop:8}}>
          <button onClick={importTemplate} disabled={!importText.trim()}>Import</button>
        </div>
      </section>

      <section style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12, marginTop:12, overflowX:'auto'}}>
        <h2 style={{marginTop:0}}>Quickstart Templates</h2>
        {!quickstart.length ? <p style={{color:'#64748b'}}>No quickstarts available</p> : (
          <div style={{display:'grid', gridTemplateColumns:'1fr', gap:8}}>
            {quickstart.map((q:any)=>(
              <div key={q.slug} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12}}>
                <div style={{display:'flex', alignItems:'center', gap:8}}>
                  <div style={{fontWeight:600}}>{q.name}</div>
                  <span style={{fontSize:12, color:'#64748b'}}>{q.purpose}</span>
                  <span style={{marginLeft:'auto', fontSize:12, color:'#64748b'}}>{q.slug}</span>
                </div>
                <div style={{marginTop:6, color:'#475569'}}>{q.description}</div>
                <div style={{marginTop:8}}>
                  <button onClick={async ()=>{
                    try{
                      const r = await fetch(`${API_BASE}/playbooks/templates/quickstart/${q.slug}`, { method:'POST', headers: token ? { Authorization:`Bearer ${token}` } : undefined });
                      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Create failed: ${r.status}`);
                      await load();
                    }catch(e:any){ setError(e.message || String(e)); }
                  }}>Create</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
