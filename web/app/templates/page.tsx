"use client";
import { useEffect, useState } from "react";

type Section = { heading: string; default_included: boolean; placeholder?: string };
type Template = { id:number; name:string; target:'trade'|'daily'; sections: Section[]; created_at?: string };

export default function TemplatesPage(){
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const [token, setToken] = useState<string>("");
  const [target, setTarget] = useState<'trade'|'daily'>("trade");
  const [items, setItems] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // create form
  const [name, setName] = useState("");
  const [sections, setSections] = useState<Section[]>([{ heading:"", default_included:true, placeholder:"" }]);

  useEffect(()=>{ try{ setToken(localStorage.getItem("ej_token") || ""); }catch{} },[]);
  useEffect(()=>{ if (token){ load(); } }, [token, target]);

  async function load(){
    setError(null); setLoading(true);
    try{
      const r = await fetch(`${API_BASE}/templates?target=${target}`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Failed: ${r.status}`);
      setItems(Array.isArray(j) ? j : []);
    }catch(e:any){ setError(e.message || String(e)); try{ (await import('../components/Toaster')).toast(e.message||'Failed','error'); }catch{} }
    finally{ setLoading(false); }
  }

  function updateSection(idx:number, patch: Partial<Section>){
    setSections(prev => prev.map((s,i)=> i===idx ? { ...s, ...patch } : s));
  }
  function addSection(){ setSections(prev => [...prev, { heading:"", default_included:true, placeholder:"" }]); }
  function removeSection(idx:number){ setSections(prev => prev.filter((_,i)=> i!==idx)); }
  function onDragStartNew(e: React.DragEvent<HTMLDivElement>, idx:number){ e.dataTransfer.setData('text/plain', String(idx)); }
  function onDropNew(e: React.DragEvent<HTMLDivElement>, idx:number){
    const from = parseInt(e.dataTransfer.getData('text/plain'),10);
    if (Number.isNaN(from) || from===idx) return;
    setSections(prev => { const arr = prev.slice(); const [m]=arr.splice(from,1); arr.splice(idx,0,m); return arr; });
  }
  function onDragOverNew(e: React.DragEvent){ e.preventDefault(); }

  async function createTemplate(){
    if (!token){ setError('Login required'); return; }
    if (!name.trim()){ setError('Name is required'); return; }
    const filtered = sections.filter(s => s.heading && s.heading.trim().length>0);
    if (!filtered.length){ setError('Add at least one section'); return; }
    try{
      const r = await fetch(`${API_BASE}/templates`, {
        method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` },
        body: JSON.stringify({ name: name.trim(), target, sections: filtered })
      });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Create failed: ${r.status}`);
      setName(""); setSections([{ heading:"", default_included:true, placeholder:"" }]);
      await load();
    }catch(e:any){ setError(e.message || String(e)); try{ (await import('../components/Toaster')).toast(e.message||'Create failed','error'); }catch{} }
  }

  async function saveTemplate(t: Template){
    if (!token) return;
    try{
      const r = await fetch(`${API_BASE}/templates/${t.id}`, {
        method:'PATCH', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` },
        body: JSON.stringify({ name: t.name, sections: t.sections })
      });
      const j = await r.json().catch(()=>({})); if (!r.ok) throw new Error(j.detail || `Save failed: ${r.status}`);
      await load();
      try{ (await import('../components/Toaster')).toast('Template saved','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); try{ (await import('../components/Toaster')).toast(e.message||'Save failed','error'); }catch{} }
  }

  async function deleteTemplate(id:number){
    if (!token) return; const ok = confirm('Delete this template?'); if (!ok) return;
    try{
      const r = await fetch(`${API_BASE}/templates/${id}`, { method:'DELETE', headers:{ Authorization:`Bearer ${token}` }});
      if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Delete failed: ${r.status}`); }
      await load();
      try{ (await import('../components/Toaster')).toast('Template deleted','success'); }catch{}
    }catch(e:any){ setError(e.message || String(e)); try{ (await import('../components/Toaster')).toast(e.message||'Delete failed','error'); }catch{} }
  }

  function updateItem(idx:number, patch: Partial<Template>){
    setItems(prev => prev.map((t,i)=> i===idx ? { ...t, ...patch } : t));
  }
  function updateItemSection(tidx:number, sidx:number, patch: Partial<Section>){
    setItems(prev => prev.map((t,i)=>{
      if (i!==tidx) return t;
      const secs = t.sections.slice(); secs[sidx] = { ...secs[sidx], ...patch } as any; return { ...t, sections: secs };
    }));
  }
  function addItemSection(tidx:number){
    setItems(prev => prev.map((t,i)=> i===tidx ? { ...t, sections: [...t.sections, { heading:"", default_included:true, placeholder:"" }] } : t));
  }
  function removeItemSection(tidx:number, sidx:number){
    setItems(prev => prev.map((t,i)=>{
      if (i!==tidx) return t; const secs = t.sections.filter((_,j)=> j!==sidx); return { ...t, sections: secs };
    }));
  }

  return (
    <main style={{maxWidth: 1000, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>Templates</h1>
      <div style={{marginBottom:8}}><a href="/dashboard">Back to Dashboard</a></div>
      {error && <p style={{color:'crimson'}}>{error}</p>}

      <div style={{display:'flex', gap:12, alignItems:'center', margin:'8px 0'}}>
        <label>Target:</label>
        <select value={target} onChange={e=> setTarget((e.target.value==='daily'?'daily':'trade'))}>
          <option value="trade">Trade</option>
          <option value="daily">Daily</option>
        </select>
        <a href="/trades" style={{marginLeft:'auto'}}>Go to Trades</a>
      </div>

      <section style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12, margin:'12px 0'}}>
        <h2 style={{marginTop:0}}>Create Template</h2>
        <div style={{display:'grid', gridTemplateColumns:'1fr', gap:8}}>
          <input placeholder="Name" value={name} onChange={e=>setName(e.target.value)} />
          <div>
            <div style={{fontWeight:600, marginBottom:6}}>Sections</div>
            {(sections||[]).map((s, idx) => (
              <div key={idx} draggable onDragStart={e=>onDragStartNew(e, idx)} onDragOver={onDragOverNew} onDrop={e=>onDropNew(e, idx)} style={{display:'grid', gridTemplateColumns:'1fr 120px 1fr auto', gap:8, alignItems:'center', marginBottom:6}}>
                <input placeholder="Heading" value={s.heading} onChange={e=>updateSection(idx,{ heading:e.target.value })} />
                <label style={{display:'flex', alignItems:'center', gap:6}}>
                  <input type="checkbox" checked={!!s.default_included} onChange={e=>updateSection(idx,{ default_included:e.target.checked })} /> Default
                </label>
                <input placeholder="Placeholder" value={s.placeholder||""} onChange={e=>updateSection(idx,{ placeholder:e.target.value })} />
                <button onClick={()=>removeSection(idx)}>Remove</button>
              </div>
            ))}
            <button onClick={addSection}>Add Section</button>
          </div>
          <div>
            <button onClick={createTemplate} disabled={loading}>{loading ? 'Working…' : 'Create'}</button>
          </div>
        </div>
      </section>

      <section style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12}}>
        <h2 style={{marginTop:0}}>Your Templates ({target})</h2>
        {loading ? <p>Loading…</p> : (!items.length ? <p style={{color:'#64748b'}}>No templates yet</p> : (
          <div style={{display:'flex', flexDirection:'column', gap:12}}>
            {items.map((t, i) => (
              <div key={t.id} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12}}>
                <div style={{display:'flex', gap:8, alignItems:'center'}}>
                  <input value={t.name} onChange={e=>updateItem(i,{ name:e.target.value })} />
                  <span style={{fontSize:12, color:'#64748b'}}>#{t.id}</span>
                  <div style={{marginLeft:'auto', display:'flex', gap:8}}>
                    <button onClick={()=>saveTemplate(items[i])}>Save</button>
                    <button onClick={()=>deleteTemplate(t.id)} style={{color:'#991b1b'}}>Delete</button>
                  </div>
                </div>
                <div style={{marginTop:8}}>
                  <div style={{fontWeight:600, marginBottom:6}}>Sections</div>
                  {t.sections.map((s, sidx) => (
                    <div key={sidx} draggable onDragStart={e=>{ e.dataTransfer.setData('text/plain', String(sidx)); }} onDragOver={e=>e.preventDefault()} onDrop={e=>{
                      const from = parseInt(e.dataTransfer.getData('text/plain'),10);
                      if (Number.isNaN(from) || from===sidx) return;
                      setItems(prev => prev.map((tt,ii)=>{
                        if (ii!==i) return tt; const arr = tt.sections.slice(); const [m]=arr.splice(from,1); arr.splice(sidx,0,m); return { ...tt, sections: arr } as any;
                      }));
                    }} style={{display:'grid', gridTemplateColumns:'1fr 120px 1fr auto', gap:8, alignItems:'center', marginBottom:6}}>
                      <input placeholder="Heading" value={s.heading} onChange={e=>updateItemSection(i, sidx, { heading:e.target.value })} />
                      <label style={{display:'flex', alignItems:'center', gap:6}}>
                        <input type="checkbox" checked={!!s.default_included} onChange={e=>updateItemSection(i, sidx, { default_included:e.target.checked })} /> Default
                      </label>
                      <input placeholder="Placeholder" value={s.placeholder||""} onChange={e=>updateItemSection(i, sidx, { placeholder:e.target.value })} />
                      <button onClick={()=>removeItemSection(i, sidx)}>Remove</button>
                    </div>
                  ))}
                  <button onClick={()=>addItemSection(i)}>Add Section</button>
                </div>
              </div>
            ))}
          </div>
        ))}
      </section>

    </main>
  );
}
