"use client";
import React, { useEffect, useState } from "react";

export default function SettingsPage(){
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const [token, setToken] = useState<string>("");
  const [rules, setRules] = useState({ max_losses_row_day: 3, max_losing_days_streak_week: 2, max_losing_weeks_streak_month: 2, alerts_enabled: true, enforcement_mode: 'off' as 'off'|'warn'|'block' });
  const [accounts, setAccounts] = useState<{id:number; name:string; account_max_risk_pct?: number|null}[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(()=>{ try{ setToken(localStorage.getItem("ej_token")||""); }catch{} },[]);
  useEffect(()=>{ if (token){ load(); } }, [token]);

  async function load(){
    setError(null);
    try{
      const [rRules, rAccts] = await Promise.all([
        fetch(`${API_BASE}/settings/trading-rules`, { headers: token ? { Authorization:`Bearer ${token}` } : undefined }),
        fetch(`${API_BASE}/accounts`, { headers: token ? { Authorization:`Bearer ${token}` } : undefined }),
      ]);
      if (rRules.ok){ const j = await rRules.json(); setRules(j); }
      if (rAccts.ok){ const j = await rAccts.json(); setAccounts(j||[]); }
    }catch(e:any){ setError(e.message||String(e)); }
  }

  async function save(){
    if (!token) return; setSaving(true);
    try{
      await fetch(`${API_BASE}/settings/trading-rules`, { method:'PUT', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(rules) });
      for (const a of accounts){
        await fetch(`${API_BASE}/accounts/${a.id}`, { method:'PATCH', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify({ account_max_risk_pct: a.account_max_risk_pct ?? null }) });
      }
      try{ (await import('../../components/Toaster')).toast('Settings saved','success'); }catch{}
    }catch(e:any){ setError(e.message||String(e)); }
    finally{ setSaving(false); }
  }

  return (
    <main style={{maxWidth: 900, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>Settings</h1>
      {error && <p style={{color:'crimson'}}>{error}</p>}
      <section style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12, marginBottom:12}}>
        <h2 style={{marginTop:0}}>Trading Rules & Alerts</h2>
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12}}>
          <label style={{display:'grid', gridTemplateColumns:'1fr 140px', gap:6, alignItems:'center'}}>
            <span>Max losses in a row (day)</span>
            <input type="number" min={1} value={rules.max_losses_row_day} onChange={e=>setRules(r=>({...r, max_losses_row_day: parseInt(e.target.value||'0',10)||0}))} />
          </label>
          <label style={{display:'grid', gridTemplateColumns:'1fr 140px', gap:6, alignItems:'center'}}>
            <span>Max losing days streak (week)</span>
            <input type="number" min={1} value={rules.max_losing_days_streak_week} onChange={e=>setRules(r=>({...r, max_losing_days_streak_week: parseInt(e.target.value||'0',10)||0}))} />
          </label>
          <label style={{display:'grid', gridTemplateColumns:'1fr 140px', gap:6, alignItems:'center'}}>
            <span>Max losing weeks streak (month)</span>
            <input type="number" min={1} value={rules.max_losing_weeks_streak_month} onChange={e=>setRules(r=>({...r, max_losing_weeks_streak_month: parseInt(e.target.value||'0',10)||0}))} />
          </label>
          <label style={{display:'grid', gridTemplateColumns:'1fr 140px', gap:6, alignItems:'center'}}>
            <span>Enforcement mode</span>
            <select value={rules.enforcement_mode} onChange={e=> setRules(r=>({...r, enforcement_mode: (e.target.value as any)}))}>
              <option value="off">Off (info only)</option>
              <option value="warn">Warn (log + alert)</option>
              <option value="block">Block (prevent)</option>
            </select>
          </label>
          <label style={{display:'grid', gridTemplateColumns:'1fr 140px', gap:6, alignItems:'center'}}>
            <span>Enable alerts</span>
            <input type="checkbox" checked={rules.alerts_enabled} onChange={e=> setRules(r=>({...r, alerts_enabled: e.target.checked}))} />
          </label>
        </div>
      </section>
      <section style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12}}>
        <h2 style={{marginTop:0}}>Accounts — Max Risk %</h2>
        {!accounts.length ? (
          <p style={{color:'#64748b'}}>No accounts yet.</p>
        ) : (
          <div style={{display:'grid', gridTemplateColumns:'1fr 160px', gap:8}}>
            {accounts.map((a, idx)=> (
              <React.Fragment key={a.id}>
                <div style={{display:'flex', alignItems:'center'}}>{a.name}</div>
                <input type="number" step={0.05} value={(a.account_max_risk_pct ?? '') as any} onChange={e=> setAccounts(prev=> prev.map((x,i)=> i===idx ? { ...x, account_max_risk_pct: e.target.value===''? null : parseFloat(e.target.value) } : x))} />
              </React.Fragment>
            ))}
          </div>
        )}
      </section>
      <div style={{display:'flex', gap:8, marginTop:12}}>
        <button onClick={save} disabled={saving}>Save</button>
        <a href="/dashboard" style={{marginLeft:'auto'}}>Back to Dashboard</a>
      </div>
    </main>
  );
}

