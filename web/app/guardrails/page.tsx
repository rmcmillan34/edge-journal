"use client";
import React, { useEffect, useState } from "react";

export default function GuardrailsPage(){
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const [token, setToken] = useState<string>("");
  const [start, setStart] = useState<string>("");
  const [end, setEnd] = useState<string>("");
  const [scope, setScope] = useState<string>("");
  const [ackFilter, setAckFilter] = useState<string>("");
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(()=>{ try{ setToken(localStorage.getItem("ej_token")||""); }catch{} },[]);
  useEffect(()=>{ if (token){
    const u = new URL(window.location.href);
    const qsStart = u.searchParams.get('start')||'';
    const qsEnd = u.searchParams.get('end')||'';
    const qsScope = u.searchParams.get('scope')||'';
    if (qsStart) setStart(qsStart);
    if (qsEnd) setEnd(qsEnd);
    if (qsScope) setScope(qsScope);
    load();
  } },[token]);

  async function load(){
    setError(null); setLoading(true);
    try{
      const qs = new URLSearchParams();
      if (start) qs.set('start', start);
      if (end) qs.set('end', end);
      if (scope) qs.set('scope', scope);
      if (ackFilter) qs.set('acknowledged', ackFilter);
      const r = await fetch(`${API_BASE}/breaches?${qs.toString()}`, { headers: token ? { Authorization:`Bearer ${token}` } : undefined });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail||`Failed: ${r.status}`);
      setItems(Array.isArray(j)? j: []);
    }catch(e:any){ setError(e.message||String(e)); }
    finally{ setLoading(false); }
  }

  async function ack(id:number){
    try{
      const r = await fetch(`${API_BASE}/breaches/${id}/ack`, { method:'POST', headers: token ? { Authorization:`Bearer ${token}` } : undefined });
      if (r.ok) setItems(prev => prev.map(x=> x.id===id ? { ...x, acknowledged:true } : x));
    }catch{}
  }

  return (
    <main style={{maxWidth:1000, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>Guardrails</h1>
      {error && <p style={{color:'crimson'}}>{error}</p>}
      <div style={{display:'flex', gap:8, alignItems:'center', margin:'8px 0', flexWrap:'wrap'}}>
        <label>Start</label>
        <input type="date" value={start} onChange={e=>setStart(e.target.value)} />
        <label>End</label>
        <input type="date" value={end} onChange={e=>setEnd(e.target.value)} />
        <label>Scope</label>
        <select value={scope} onChange={e=>setScope(e.target.value)}>
          <option value="">Any</option>
          <option value="day">day</option>
          <option value="week">week</option>
          <option value="month">month</option>
          <option value="trade">trade</option>
        </select>
        <label>Acknowledged</label>
        <select value={ackFilter} onChange={e=>setAckFilter(e.target.value)}>
          <option value="">Any</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
        <button onClick={load} disabled={loading}>Apply</button>
        <a href="/dashboard" style={{marginLeft:'auto'}}>Back to Dashboard</a>
      </div>
      {!items.length ? (
        <p style={{color:'#64748b'}}>{loading ? 'Loading…' : 'No breaches'}</p>
      ) : (
        <table style={{width:'100%'}}>
          <thead className="tbl-head">
            <tr>
              <th style={{textAlign:'left'}}>Date/Week</th>
              <th style={{textAlign:'left'}}>Scope</th>
              <th style={{textAlign:'left'}}>Rule</th>
              <th style={{textAlign:'left'}}>Summary</th>
              <th style={{textAlign:'left'}}>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map(b=>{
              const d = b.details || {}; const label = b.rule_key;
              const summary = label === 'risk_cap_exceeded' ? `Intended ${d.intended ?? '?'}% > Cap ${d.cap ?? '?'}% (grade ${d.grade ?? '?'})` : JSON.stringify(d);
              return (
                <tr key={b.id}>
                  <td>{b.date_or_week}</td>
                  <td>{b.scope}</td>
                  <td>{label}</td>
                  <td>{summary}</td>
                  <td>{b.acknowledged ? 'Acknowledged' : 'Unacknowledged'}</td>
                  <td style={{textAlign:'right'}}>
                    {!b.acknowledged && <button onClick={()=>ack(b.id)}>Acknowledge</button>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </main>
  );
}

