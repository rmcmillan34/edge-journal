"use client";
import { useEffect, useState } from "react";

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
  const [tab, setTab] = useState<'overview'|'notes'|'attachments'>("overview");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [notes, setNotes] = useState("");
  const [postNotes, setPostNotes] = useState("");
  const [attMeta, setAttMeta] = useState({ timeframe:"", state:"", view:"", caption:"", reviewed:false });
  const [files, setFiles] = useState<FileList | null>(null);
  const [tpls, setTpls] = useState<any[]>([]);
  const [tplId, setTplId] = useState<number | "">("");
  const [tplChecks, setTplChecks] = useState<Record<number, boolean>>({});
  const [attSel, setAttSel] = useState<number[]>([]);
  const [reorderMode, setReorderMode] = useState(false);

  useEffect(()=>{ try { setToken(localStorage.getItem("ej_token") || ""); } catch{} },[]);
  useEffect(()=>{ if (token){ reload(); loadTemplates(); } }, [token]);

  async function loadTemplates(){
    try{
      const r = await fetch(`${API_BASE}/templates?target=trade`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (r.ok){ const j = await r.json(); setTpls(Array.isArray(j)?j:[]); }
    }catch{}
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
      try{ (await import('../../components/Toaster')).toast('Notes saved','success'); }catch{}
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
      try{ (await import('../../components/Toaster')).toast('Attachments uploaded','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setSaving(false); }
  }

  async function delAtt(id:number){
    if (!token) return; const ok = confirm('Delete attachment?'); if (!ok) return;
    try{
      const r = await fetch(`${API_BASE}/trades/${params.id}/attachments/${id}`, { method:'DELETE', headers:{ Authorization:`Bearer ${token}` }});
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Delete failed: ${r.status}`); }
      await reload();
      try{ (await import('../../components/Toaster')).toast('Attachment deleted','success'); }catch{}
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
      try{ (await import('../../components/Toaster')).toast('Deleted selected attachments','success'); }catch{}
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
      try{ (await import('../../components/Toaster')).toast('Reordered attachments','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); }
  }

  return (
    <main style={{maxWidth: 1000, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>Trade #{params.id}</h1>
      {error && <p style={{color:'crimson'}}>{error}</p>}
      {!data ? <p>Loading…</p> : (
        <>
          <div style={{display:'flex', gap:8, marginBottom:8}}>
            <button onClick={()=>setTab('overview')} disabled={tab==='overview'}>Overview</button>
            <button onClick={()=>setTab('notes')} disabled={tab==='notes'}>Notes</button>
            <button onClick={()=>setTab('attachments')} disabled={tab==='attachments'}>Attachments</button>
            <a href="/trades" style={{marginLeft:'auto'}}>Back to Trades</a>
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
              <textarea rows={8} value={notes} onChange={e=>setNotes(e.target.value)} style={{width:'100%'}} />
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
                          {reorderMode && <span style={{color:'#64748b', fontSize:12, userSelect:'none'}}>Drag to reorder</span>}
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
        </>
      )}
    </main>
  );
}
