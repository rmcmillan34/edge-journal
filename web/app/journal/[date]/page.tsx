"use client";
import { useEffect, useState } from "react";

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

  useEffect(()=>{ try{ setToken(localStorage.getItem("ej_token") || ""); }catch{} }, []);
  useEffect(()=>{ if (token){ reload(); loadTrades(); loadTemplates(); } }, [token, d]);

  async function loadTemplates(){
    try{
      const r = await fetch(`${API_BASE}/templates?target=daily`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (r.ok){ const j = await r.json(); setTpls(Array.isArray(j)?j:[]); }
    }catch{}
  }

  async function reload(){
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

  async function createTemplateFromNotes(){
    if (!token){ setError('Login required'); return; }
    const name = prompt('Template name for Daily notes?');
    if (!name) return;
    const lines = (notes||'').split(/\r?\n/);
    const sections: any[] = [];
    let current: { heading: string; placeholder?: string } | null = null;
    for (const ln of lines){
      const m = ln.match(/^#{2,3}\s+(.+)/);
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
    <main style={{maxWidth: 1000, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>Daily Journal — {d}</h1>
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
                setNotes(prev => (prev ? prev+"\n\n" : "") + parts.join("\n"));
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
        <textarea rows={10} value={notes} onChange={e=>setNotes(e.target.value)} style={{width:'100%'}} />
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
              {!atts.length ? <p style={{color:'#64748b'}}>No attachments</p> : (
                <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(160px, 1fr))', gap:12}}>
                  {atts.map(a => (
                    <div key={a.id} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:8}}>
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
  );
}
