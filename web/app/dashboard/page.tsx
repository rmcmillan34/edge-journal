"use client";
import { useEffect, useMemo, useState } from "react";

type Metrics = {
  trades_total: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  net_pnl_sum: number;
  equity_curve: { date: string; net_pnl: number; equity: number }[];
  unreviewed_count?: number;
};

type CalendarDay = { date: string; trades: number; net_pnl: number; breaches: string[] };

function fmtYmd(d: Date){
  const y = d.getFullYear();
  const m = String(d.getMonth()+1).padStart(2,'0');
  const da = String(d.getDate()).padStart(2,'0');
  return `${y}-${m}-${da}`;
}

export default function Dashboard(){
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const [token, setToken] = useState<string>("");
  const [data, setData] = useState<Metrics | null>(null);
  const [allData, setAllData] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [monthAnchor, setMonthAnchor] = useState<Date>(()=>{
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [symbol, setSymbol] = useState("");
  const [account, setAccount] = useState("");
  const [displayTz, setDisplayTz] = useState<string>("");
  const [symbols, setSymbols] = useState<string[]>([]);
  const [accountsList, setAccountsList] = useState<{id:number; name:string}[]>([]);
  const [journalDates, setJournalDates] = useState<string[]>([]);
  const [calendarDays, setCalendarDays] = useState<CalendarDay[]>([]);
  const [rulesModalOpen, setRulesModalOpen] = useState<boolean>(false);
  const [rules, setRules] = useState({ max_losses_row_day: 3, max_losing_days_streak_week: 2, max_losing_weeks_streak_month: 2, alerts_enabled: true });
  const [acctCaps, setAcctCaps] = useState<{ id:number; name:string; account_max_risk_pct?: number|null }[]>([]);
  const [weekStart, setWeekStart] = useState<'Mon'|'Sun'>(()=>{
    try{ return (localStorage.getItem('dash_week_start') as any) || 'Mon'; }catch{ return 'Mon'; }
  });
  const [hideWeekends, setHideWeekends] = useState<boolean>(()=>{ try{ return localStorage.getItem('dash_hide_weekends') === '1'; }catch{ return false; } });

  useEffect(() => { try {
    // hydrate client-only state to avoid hydration mismatches
    setMounted(true);
    setToken(localStorage.getItem("ej_token") || "");
    setDisplayTz(localStorage.getItem("ej_display_tz") || "");
    const s = localStorage.getItem('dash_symbol') || '';
    const a = localStorage.getItem('dash_account') || '';
    const ym = localStorage.getItem('dash_month_anchor') || '';
    if (s) setSymbol(s);
    if (a) setAccount(a);
    if (ym){
      const [y,m] = ym.split('-').map(x=>parseInt(x,10));
      if (!Number.isNaN(y) && !Number.isNaN(m)) setMonthAnchor(new Date(y, m-1, 1));
    }
  } catch{} }, []);
  useEffect(() => { if (token) load(); }, [token, monthAnchor, symbol, account, displayTz]);
  useEffect(() => {
    if (!token) return;
    // first-run wizard trigger
    try{
      const done = localStorage.getItem('ej_rules_setup_done') === '1';
      if (!done){
        openRulesWizard();
      }
    }catch{}
  }, [token]);
  useEffect(() => { // load symbols (optionally filtered by account)
    async function loadSymbols(){
      if (!token) return;
      try{
        const qs = account ? `?account=${encodeURIComponent(account)}` : '';
        const r = await fetch(`${API_BASE}/trades/symbols${qs}`, { headers: { Authorization: `Bearer ${token}` }});
        if (r.ok){ const j = await r.json(); setSymbols(j || []); }
      }catch{}
    }
    loadSymbols();
  }, [token, account]);

  useEffect(() => { // load accounts for datalist
    async function loadAccounts(){
      if (!token) return;
      try{
        const r = await fetch(`${API_BASE}/accounts`, { headers: { Authorization: `Bearer ${token}` }});
        if (r.ok){ const j = await r.json(); setAccountsList(j || []); }
      }catch{}
    }
    loadAccounts();
  }, [token]);

  async function load(){
    setError(null); setLoading(true);
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
    // small retry helper (network hiccups / service warm-up)
    const fetchJson = async (url: string, tries = 3, delayMs = 400): Promise<{ ok:boolean; status:number; json:any }> => {
      let lastErr: any = null;
      for (let i=0;i<tries;i++){
        try{
          const r = await fetch(url, { headers });
          const j = await r.json().catch(() => ({}));
          return { ok: r.ok, status: r.status, json: j };
        }catch(err){ lastErr = err; }
        if (i < tries-1) await new Promise(res => setTimeout(res, delayMs));
      }
      throw lastErr || new Error('Network error');
    };

    try{
      const start = new Date(monthAnchor.getFullYear(), monthAnchor.getMonth(), 1);
      const end = new Date(monthAnchor.getFullYear(), monthAnchor.getMonth()+1, 0);
      const qp = new URLSearchParams({ start: fmtYmd(start), end: fmtYmd(end) });
      if (symbol) qp.set('symbol', symbol);
      if (account) qp.set('account', account);
      if (displayTz) qp.set('tz', displayTz);
      const all = new URLSearchParams();
      if (symbol) all.set('symbol', symbol);
      if (account) all.set('account', account);
      if (displayTz) all.set('tz', displayTz);

      // Fetch primary metrics with retry; handle 401 gracefully
      const rm = await fetchJson(`${API_BASE}/metrics?${qp.toString()}`);
      if (rm.status === 401 || rm.status === 403){
        setToken("");
        setError('Please sign in');
        return;
      }
      if (!rm.ok) throw new Error(rm.json?.detail || `Failed: ${rm.status}`);
      setData(rm.json);

      // Fetch all-time metrics and journal dates, but do not block UI if they fail
      try{
        const ra = await fetchJson(`${API_BASE}/metrics?${all.toString()}`, 2, 300);
        if (ra.ok) setAllData(ra.json);
      }catch{}
      try{
        const rj = await fetchJson(`${API_BASE}/journal/dates?start=${fmtYmd(start)}&end=${fmtYmd(end)}&with_counts=1`, 2, 300);
        if (rj.ok) setJournalDates(Array.isArray(rj.json) ? rj.json : []);
      }catch{}
      try{
        const rc = await fetchJson(`${API_BASE}/metrics/calendar?start=${fmtYmd(start)}&end=${fmtYmd(end)}${displayTz?`&tz=${encodeURIComponent(displayTz)}`:''}`, 2, 300);
        if (rc.ok && rc.json && Array.isArray(rc.json.days)) setCalendarDays(rc.json.days);
      }catch{}
    }catch(e:any){ setError(e.message || 'Failed to load metrics'); }
    finally{ setLoading(false); }
  }

  async function openRulesWizard(){
    try{
      // load current rules and accounts
      const [rRules, rAccts] = await Promise.all([
        fetch(`${API_BASE}/settings/trading-rules`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined }),
        fetch(`${API_BASE}/accounts`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined }),
      ]);
      if (rRules.ok){ const j = await rRules.json(); setRules(j); }
      if (rAccts.ok){ const j = await rAccts.json(); setAcctCaps((j||[]).map((a:any)=>({ id:a.id, name:a.name, account_max_risk_pct:a.account_max_risk_pct })) ); }
      setRulesModalOpen(true);
    }catch{}
  }

  async function saveRulesWizard(){
    try{
      await fetch(`${API_BASE}/settings/trading-rules`, { method:'PUT', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(rules) });
      for (const a of acctCaps){
        await fetch(`${API_BASE}/accounts/${a.id}`, { method:'PATCH', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify({ account_max_risk_pct: a.account_max_risk_pct ?? null }) });
      }
      try{ localStorage.setItem('ej_rules_setup_done','1'); }catch{}
      setRulesModalOpen(false);
    }catch{}
  }

  const chart = useMemo(() => {
    const src = (allData && allData.equity_curve?.length) ? allData : data;
    if (!src || !src.equity_curve?.length) return null;
    const points = src.equity_curve;
    const W = 640, H = 200, P = 20;
    const xs = points.map((_,i)=>i);
    const ys = points.map(p=>p.equity);
    const xmin = 0, xmax = xs.length > 1 ? xs.length - 1 : 1;
    const ymin = Math.min(...ys, 0), ymax = Math.max(...ys, 0.0001);
    const xscale = (x:number) => P + (x - xmin) / (xmax - xmin) * (W - 2*P);
    const yscale = (y:number) => H - P - (y - ymin) / (ymax - ymin) * (H - 2*P);
    const d = points.map((p,i)=> `${i===0?'M':'L'} ${xscale(i).toFixed(1)} ${yscale(p.equity).toFixed(1)}`).join(' ');
    return (
      <ChartSVG W={W} H={H} P={P} d={d} points={points} />
    );
  }, [data, allData]);

  return (
    <main style={{maxWidth: 1000, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>Dashboard</h1>
      {rulesModalOpen && (
        <div style={{position:'fixed', inset:0, background:'rgba(0,0,0,0.4)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:50}}>
          <div style={{background:'#fff', borderRadius:8, padding:16, width:600, maxWidth:'90%'}}>
            <h2 style={{marginTop:0}}>Configure Risk & Rules</h2>
            <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12}}>
              <div>
                <div style={{fontWeight:600, marginBottom:6}}>Trading Rules</div>
                <label style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:6, alignItems:'center'}}>
                  <span>Max losses in a row (day)</span>
                  <input type="number" min={1} value={rules.max_losses_row_day} onChange={e=>setRules(r=>({...r, max_losses_row_day: parseInt(e.target.value||'0',10)||0}))} />
                </label>
                <label style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:6, alignItems:'center'}}>
                  <span>Max losing days streak (week)</span>
                  <input type="number" min={1} value={rules.max_losing_days_streak_week} onChange={e=>setRules(r=>({...r, max_losing_days_streak_week: parseInt(e.target.value||'0',10)||0}))} />
                </label>
                <label style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:6, alignItems:'center'}}>
                  <span>Max losing weeks streak (month)</span>
                  <input type="number" min={1} value={rules.max_losing_weeks_streak_month} onChange={e=>setRules(r=>({...r, max_losing_weeks_streak_month: parseInt(e.target.value||'0',10)||0}))} />
                </label>
                <label style={{display:'flex', alignItems:'center', gap:8, marginTop:8}}>
                  <input type="checkbox" checked={rules.alerts_enabled} onChange={e=>setRules(r=>({...r, alerts_enabled: e.target.checked}))} /> Enable alerts
                </label>
              </div>
              <div>
                <div style={{fontWeight:600, marginBottom:6}}>Account Max Risk %</div>
                {!acctCaps.length ? <div style={{color:'#64748b'}}>No accounts yet. You can set caps later.</div> : (
                  <div style={{display:'flex', flexDirection:'column', gap:8}}>
                    {acctCaps.map((a, idx) => (
                      <label key={a.id} style={{display:'grid', gridTemplateColumns:'1fr 120px', gap:8, alignItems:'center'}}>
                        <span>{a.name}</span>
                        <input type="number" step={0.05} value={(a.account_max_risk_pct ?? '') as any} onChange={e=> setAcctCaps(prev => prev.map((x,i)=> i===idx ? { ...x, account_max_risk_pct: e.target.value===''? null : parseFloat(e.target.value) } : x ))} />
                      </label>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div style={{display:'flex', justifyContent:'flex-end', gap:8, marginTop:12}}>
              <button onClick={()=>setRulesModalOpen(false)}>Close</button>
              <button onClick={saveRulesWizard}>Save</button>
            </div>
          </div>
        </div>
      )}
      {mounted && !token && (
        <div className="notice" style={{margin:'8px 0', padding:'8px 12px', border:'1px solid #fde68a', background:'#fffbeb', color:'#92400e', borderRadius:8}}>
          Please <a href="/auth/login">sign in</a> to view metrics.
        </div>
      )}
      {error && <p style={{color:'crimson'}}>{error}</p>}
      <div style={{display:'flex', gap:8, margin:'8px 0', flexWrap:'wrap', alignItems:'center'}}>
        <div>
          <input list="symbol-list" placeholder="Symbol contains" value={symbol} onChange={e=>setSymbol(e.target.value)} />
          <datalist id="symbol-list">
            {(Array.isArray((symbols as any)) ? (symbols as any) : []).map((s:string) => (<option key={s} value={s} />))}
          </datalist>
        </div>
        <div>
          <input list="account-list" placeholder="Account contains" value={account} onChange={e=>setAccount(e.target.value)} />
          <datalist id="account-list">
            {accountsList.map(a => (<option key={a.id} value={a.name} />))}
          </datalist>
        </div>
        <div style={{display:'flex', alignItems:'center', gap:6}}>
          <label>Display timezone:</label>
          <select
            value={displayTz}
            onChange={e=>{ const v = e.target.value; setDisplayTz(v); try{ localStorage.setItem("ej_display_tz", v);}catch{} }}
          >
            <option value="">UTC</option>
            {["Australia/Sydney","America/New_York","Europe/London","Asia/Singapore"].map(z => (<option key={z} value={z}>{z}</option>))}
          </select>
        </div>
        <div style={{display:'flex', alignItems:'center', gap:6}}>
          <label>Week starts:</label>
          <select value={weekStart} onChange={e=>{ const v = (e.target.value==='Sun'?'Sun':'Mon') as 'Mon'|'Sun'; setWeekStart(v); try{ localStorage.setItem('dash_week_start', v);}catch{} }}>
            <option value="Mon">Mon</option>
            <option value="Sun">Sun</option>
          </select>
        </div>
        <label style={{display:'inline-flex',alignItems:'center', gap:6}}>
          <input type="checkbox" checked={hideWeekends} onChange={e=>{ setHideWeekends(e.target.checked); try{ localStorage.setItem('dash_hide_weekends', e.target.checked ? '1' : '0'); }catch{} }} /> Hide weekends
        </label>
        <button type="button" onClick={()=>{
          setSymbol(""); setAccount(""); setDisplayTz("");
          try{
            localStorage.removeItem('dash_symbol');
            localStorage.removeItem('dash_account');
            localStorage.setItem('ej_display_tz','');
          }catch{}
        }}>Clear Filters</button>
        {loading && <span style={{color:'#64748b'}}>Loading…</span>}
      </div>
      <div style={{display:'grid', gridTemplateColumns:'repeat(5, minmax(0, 1fr))', gap:12, margin:'12px 0'}}>
        <div style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12}}>
          <div style={{fontSize:12, color:'#64748b'}}>Trades</div>
          <div style={{fontSize:24}}>{data?.trades_total ?? '-'}</div>
        </div>
        <div style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12}}>
          <div style={{fontSize:12, color:'#64748b'}}>Win Rate</div>
          <div style={{fontSize:24}}>{data?.win_rate != null ? `${(data.win_rate*100).toFixed(1)}%` : '-'}</div>
        </div>
        <div style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12}}>
          <div style={{fontSize:12, color:'#64748b'}}>Net PnL</div>
          <div style={{fontSize:24, color:(data?.net_pnl_sum ?? 0) >= 0 ? 'green' : 'crimson'}}>{data?.net_pnl_sum ?? '-'}</div>
        </div>
        <div style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12}}>
          <div style={{fontSize:12, color:'#64748b'}}>Wins / Losses</div>
          <div style={{fontSize:24}}>{(data?.wins ?? '-')}/{(data?.losses ?? '-')}</div>
        </div>
        <div style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12}}>
          <div style={{fontSize:12, color:'#64748b'}}>Unreviewed</div>
          <div style={{fontSize:24}}>{data?.unreviewed_count ?? '-'}</div>
        </div>
      </div>
      <h2 style={{marginTop:16}}>Equity Curve (All time)</h2>
      {data?.equity_curve?.length ? (
        <div>{chart}</div>
      ) : (
        <p style={{color:'#64748b'}}>{loading ? 'Loading…' : 'No data yet'}</p>
      )}

      <h2 style={{marginTop:16}}>Calendar (Current Month)</h2>
      <Calendar monthAnchor={monthAnchor} setMonthAnchor={(d:Date)=>{ setMonthAnchor(d); try{ localStorage.setItem('dash_month_anchor', `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`);}catch{} }} daily={(calendarDays||[]).map(d=>({date:d.date, pnl:d.net_pnl}))} breachesMap={Object.fromEntries((calendarDays||[]).map(d=>[d.date, d.breaches||[]]))} loading={loading} journalDates={journalDates} hideWeekends={hideWeekends} weekStart={weekStart} />
    </main>
  );
}

function ChartSVG({ W, H, P, d, points }:{ W:number; H:number; P:number; d:string; points: {date:string; net_pnl:number; equity:number}[] }){
  const [hover, setHover] = useState<{i:number;x:number;y:number} | null>(null);
  const xmin = 0, xmax = points.length > 1 ? points.length - 1 : 1;
  const ys = points.map(p=>p.equity);
  const ymin = Math.min(...ys, 0), ymax = Math.max(...ys, 0.0001);
  const xscale = (x:number) => P + (x - xmin) / (xmax - xmin) * (W - 2*P);
  const yscale = (y:number) => H - P - (y - ymin) / (ymax - ymin) * (H - 2*P);
  function onMove(e: any){
    const rect = (e.target as SVGElement).closest('svg')!.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const rel = Math.max(0, Math.min(1, (x - P) / Math.max(1,(W - 2*P))));
    const i = Math.round(rel * (points.length - 1));
    setHover({ i, x: xscale(i), y: yscale(points[i].equity) });
  }
  return (
    <div style={{position:'relative', display:'inline-block'}}>
      <svg width={W} height={H} style={{border:'1px solid #e5e7eb', background:'#fff'}} onMouseMove={onMove} onMouseLeave={()=>setHover(null)}>
        <path d={d} fill="none" stroke="#0ea5e9" strokeWidth={2} />
        {hover && (
          <>
            <line x1={hover.x} x2={hover.x} y1={P} y2={H-P} stroke="#94a3b8" strokeDasharray="4 4" />
            <circle cx={hover.x} cy={hover.y} r={3} fill="#0ea5e9" />
          </>
        )}
      </svg>
      {hover && (
        <div style={{position:'absolute', left: hover.x+8, top: Math.max(0, hover.y-30), background:'#111827', color:'#fff', padding:'4px 6px', borderRadius:4, fontSize:12, pointerEvents:'none'}}>
          <div>{points[hover.i].date}</div>
          <div>Equity: {points[hover.i].equity.toFixed(2)}</div>
          <div>Net: {points[hover.i].net_pnl.toFixed(2)}</div>
        </div>
      )}
    </div>
  );
}

type JournalDateInfo = string | { date: string; attachment_count?: number };
function Calendar({ monthAnchor, setMonthAnchor, daily, breachesMap, loading, journalDates, hideWeekends, weekStart }:{ monthAnchor: Date; setMonthAnchor:(d:Date)=>void; daily: {date:string; pnl:number}[]; breachesMap?: Record<string,string[]>; loading:boolean; journalDates?: JournalDateInfo[]; hideWeekends?: boolean; weekStart?: 'Mon'|'Sun' }){
  const monthName = monthAnchor.toLocaleString(undefined, { month:'long', year:'numeric' });
  const [legendOpen, setLegendOpen] = useState(false);
  const breachLabels: Record<string,string> = {
    loss_streak_day: 'Loss streak exceeded (day)',
    losing_days_week: 'Losing day streak exceeded (week)',
    losing_weeks_month: 'Losing week streak exceeded (month)',
    risk_cap_exceeded: 'Risk cap exceeded (min of template/grade/account caps)'
  };
  const first = new Date(monthAnchor.getFullYear(), monthAnchor.getMonth(), 1);
  const last = new Date(monthAnchor.getFullYear(), monthAnchor.getMonth()+1, 0);
  const daysInMonth = last.getDate();
  const startIdx = (weekStart === 'Sun') ? 0 : 1;
  const weekOrder = (startIdx===1 ? [1,2,3,4,5,6,0] : [0,1,2,3,4,5,6]);
  const visibleDays = weekOrder.filter(d => hideWeekends ? (d !== 0 && d !== 6) : true);
  const cols = visibleDays.length; // 5 or 7
  const headers = (startIdx===1?["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]:["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]).filter((_,i)=> visibleDays.includes(weekOrder[i]));
  const firstIdx = visibleDays.indexOf(first.getDay());
  const dayMap = new Map(daily.map(d=>[d.date, d.pnl]));
  const jdMap = new Map<string, number>();
  (journalDates||[]).forEach((x:any)=>{ if (typeof x === 'string') jdMap.set(x, 1); else if (x && x.date) jdMap.set(x.date, Number(x.attachment_count||0)); });

  const cells: JSX.Element[] = [];
  for (let k=0; k<(firstIdx<0?0:firstIdx); k++){
    cells.push(<div key={`e-${k}`} className="cal-cell empty" style={{border:'1px solid #eee', minHeight:80, background:'var(--cal-day-bg)', color:'var(--cal-day-color)', ['--cal-day-bg' as any]:'#fafafa', ['--cal-day-color' as any]:'#334155'}} />);
  }
  for (let dayNum=1; dayNum<=daysInMonth; dayNum++){
      const d = new Date(monthAnchor.getFullYear(), monthAnchor.getMonth(), dayNum);
      if (!visibleDays.includes(d.getDay())) continue;
      const ymd = fmtYmd(d);
      const pn = dayMap.get(ymd);
      const attCount = jdMap.get(ymd) || 0;
      const hasJournal = jdMap.has(ymd);
      const baseVars:any = { ['--cal-day-bg']:'#f8fafc', ['--cal-badge-bg']:'#e2e8f0', ['--cal-day-color']:'#334155' };
      const cls = ['cal-cell','day'];
      if (pn != null){
        if (pn > 0){ baseVars['--cal-day-bg'] = '#dcfce7'; baseVars['--cal-badge-bg'] = '#bbf7d0'; baseVars['--cal-day-color'] = '#166534'; cls.push('pos'); }
        else if (pn < 0){ baseVars['--cal-day-bg'] = '#fee2e2'; baseVars['--cal-badge-bg'] = '#fecaca'; baseVars['--cal-day-color'] = '#991b1b'; cls.push('neg'); }
      }
      const breaches = (breachesMap && breachesMap[ymd]) || [];
      cells.push(
        <div key={ymd} className={cls.join(' ')} style={{border:'1px solid #e5e7eb', minHeight:92, padding:8, background:'var(--cal-day-bg)', color:'var(--cal-day-color)', cursor:'pointer', ...baseVars}} onClick={()=>{
          window.location.href = `/trades?start=${ymd}&end=${ymd}`;
        }}>
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
            <div style={{fontSize:12, opacity:0.7, display:'flex', alignItems:'center', gap:6}}>
              <span>{d.toLocaleDateString(undefined,{ day:'2-digit'})}</span>
              <a href={`/journal/${ymd}`} title="Open Journal" style={{textDecoration:'none'}} onClick={e=>e.stopPropagation()}>📝</a>
              {hasJournal && <span title="Journal exists" style={{display:'inline-block', width:8, height:8, borderRadius:9999, background:'#0ea5e9'}} />}
              {attCount > 0 && <span title={`${attCount} attachment(s)`} style={{display:'inline-block', marginLeft:4, padding:'0 6px', borderRadius:9999, background:'#0ea5e9', color:'#fff', fontSize:10}}>×{attCount}</span>}
              {!!breaches.length && (
                <span style={{display:'inline-flex', gap:4, marginLeft:6}}>
                  {breaches.includes('loss_streak_day') && <span title={breachLabels.loss_streak_day} aria-label={breachLabels.loss_streak_day}>⚠️</span>}
                  {breaches.includes('losing_days_week') && <span title={breachLabels.losing_days_week} aria-label={breachLabels.losing_days_week}>🟨</span>}
                  {breaches.includes('losing_weeks_month') && <span title={breachLabels.losing_weeks_month} aria-label={breachLabels.losing_weeks_month}>🟧</span>}
                  {breaches.includes('risk_cap_exceeded') && <span title={breachLabels.risk_cap_exceeded} aria-label={breachLabels.risk_cap_exceeded}>⛔</span>}
                </span>
              )}
            </div>
            {pn != null && (
              <span className="pnl-badge" style={{fontSize:12, background:'var(--cal-badge-bg)', color:'var(--cal-day-color)', padding:'2px 6px', borderRadius:999}}>{pn>0?'+':''}{pn.toFixed(2)}</span>
            )}
          </div>
        </div>
      );
  }

  return (
    <div>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', margin:'8px 0'}}>
        <div style={{fontWeight:600}}>{monthName}</div>
        <div style={{display:'flex', gap:8, alignItems:'center'}}>
          <button onClick={()=> setLegendOpen(v=>!v)} title="Show breach legend">Legend</button>
          <button onClick={()=> setMonthAnchor(new Date(monthAnchor.getFullYear(), monthAnchor.getMonth()-1, 1))}>&lt;</button>
          <button onClick={()=> setMonthAnchor(new Date())}>Today</button>
          <button onClick={()=> setMonthAnchor(new Date(monthAnchor.getFullYear(), monthAnchor.getMonth()+1, 1))}>&gt;</button>
        </div>
      </div>
      {legendOpen && (
        <div style={{border:'1px solid #e5e7eb', borderRadius:8, padding:8, marginBottom:8, background:'#f8fafc'}}>
          <div style={{fontWeight:600, marginBottom:6}}>Breach Legend</div>
          <div style={{display:'grid', gridTemplateColumns:'1fr 4fr', gap:8, alignItems:'center'}}>
            <div><span title={breachLabels.loss_streak_day}>⚠️</span></div>
            <div>{breachLabels.loss_streak_day}</div>
            <div><span title={breachLabels.losing_days_week}>🟨</span></div>
            <div>{breachLabels.losing_days_week}</div>
            <div><span title={breachLabels.losing_weeks_month}>🟧</span></div>
            <div>{breachLabels.losing_weeks_month}</div>
            <div><span title={breachLabels.risk_cap_exceeded}>⛔</span></div>
            <div>{breachLabels.risk_cap_exceeded}</div>
          </div>
        </div>
      )}
      <div className="cal-grid" style={{display:'grid', gridTemplateColumns:`repeat(${cols}, 1fr)`, gap:0, border:'1px solid #e5e7eb'}}>
        {headers.map((w,i)=>(
          <div key={i} className="cal-weekhead" style={{borderRight:'1px solid #e5e7eb', padding:6, background:'#f8fafc', fontSize:12, textAlign:'center'}}>{w}</div>
        ))}
        {cells}
      </div>
      {!cells.length && !loading && (
        <p style={{color:'#64748b'}}>No data for this month.</p>
      )}
    </div>
  );
}
