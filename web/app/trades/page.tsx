"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { FilterBuilder, FilterChips, FilterDSL } from "../components/filters";

type Trade = {
  id: number; account_name?: string | null; symbol?: string | null; side: string;
  qty_units?: number | null; entry_price?: number | null; exit_price?: number | null;
  open_time_utc: string; close_time_utc?: string | null; net_pnl?: number | null;
  external_trade_id?: string | null;
};

export default function TradesPage(){
  return (
    <Suspense fallback={<div style={{maxWidth:1000,margin:'2rem auto',fontFamily:'system-ui,sans-serif'}}>Loading…</div>}>
      <TradesView />
    </Suspense>
  );
}

function TradesView(){
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const searchParams = useSearchParams();
  const router = useRouter();
  const [token, setToken] = useState<string>("");
  const [mounted, setMounted] = useState(false);
  const [symbol, setSymbol] = useState("");
  const [account, setAccount] = useState("");
  const [displayTz, setDisplayTz] = useState<string>("");
  const [gradeFilter, setGradeFilter] = useState<string>("");
  const [gradesMap, setGradesMap] = useState<Record<number, string>>({});
  const [showAdd, setShowAdd] = useState(false);
  const [addBusy, setAddBusy] = useState(false);
  const [form, setForm] = useState({
    account_name: "",
    symbol: "",
    side: "Buy",
    open_date: "",
    open_time: "",
    close_date: "",
    close_time: "",
    qty_units: "",
    entry_price: "",
    exit_price: "",
    fees: "",
    net_pnl: "",
    notes_md: "",
    tz: "",
  });
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [sort, setSort] = useState<string>("open_time_utc:desc");
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(50);
  const [lastDeleted, setLastDeleted] = useState<any[]>([]);
  const [items, setItems] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<{id:number; name:string}[]>([]);
  const [symbols, setSymbols] = useState<string[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [journalOpen, setJournalOpen] = useState(false);
  const [journalText, setJournalText] = useState("");
  const [activeFilters, setActiveFilters] = useState<FilterDSL | null>(null);

  useEffect(() => {
    try {
      setToken(localStorage.getItem("ej_token") || "");
      const saved = localStorage.getItem("ej_display_tz") || "";
      setDisplayTz(saved);
      const savedTz = localStorage.getItem("ej_tz") || "";
      setForm(f=>({ ...f, tz: savedTz || f.tz }));
      const s = searchParams?.get('start') || '';
      const e = searchParams?.get('end') || '';
      const sym = searchParams?.get('symbol') || '';
      const acc = searchParams?.get('account') || '';
      const sortParam = searchParams?.get('sort') || '';
      const filtersParam = searchParams?.get('filters') || '';
      if (s) setStartDate(s);
      if (e) setEndDate(e);
      if (sym) setSymbol(sym);
      if (acc) setAccount(acc);
      if (sortParam) setSort(sortParam);
      if (filtersParam) {
        try {
          const parsed = JSON.parse(decodeURIComponent(filtersParam));
          setActiveFilters(parsed);
        } catch {}
      }
      // If no URL params, restore saved filters
      if (!s && !e && !sym && !acc && !sortParam){
        const lsStart = localStorage.getItem('trades_start') || '';
        const lsEnd = localStorage.getItem('trades_end') || '';
        const lsSort = localStorage.getItem('trades_sort') || '';
        const lsPageSize = localStorage.getItem('trades_page_size') || '';
        if (lsStart) setStartDate(lsStart);
        if (lsEnd) setEndDate(lsEnd);
        if (lsSort) setSort(lsSort);
        if (lsPageSize) setPageSize(parseInt(lsPageSize,10) || 50);
      }
    } catch {}
    setMounted(true);
  }, [searchParams]);

  // Load accounts for account dropdown (datalist)
  useEffect(() => {
    async function loadAccounts(){
      if (!token) return;
      try{
        const r = await fetch(`${API_BASE}/accounts`, { headers: { Authorization: `Bearer ${token}` }});
        if (r.ok){ const j = await r.json(); setAccounts(j || []); }
      }catch{}
    }
    loadAccounts();
  }, [token]);

  // Load symbols for symbol dropdown (optionally filtered by account filter)
  useEffect(() => {
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

  async function load(){
    setError(null); setLoading(true);
    try {
      const params = new URLSearchParams();
      if (symbol) params.set("symbol", symbol);
      if (account) params.set("account", account);
      if (startDate) params.set("start", startDate);
      if (endDate) params.set("end", endDate);
      params.set("limit", String(pageSize));
      params.set("offset", String((page-1)*pageSize));
      if (sort) params.set("sort", sort);
      if (activeFilters) {
        params.set("filters", JSON.stringify(activeFilters));
      }
      const r = await fetch(`${API_BASE}/trades?${params.toString()}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || `Failed: ${r.status}`);
      setItems(j);
      // Load playbook grades for current page
      try{
        const ids = (j||[]).map((t:any)=>t.id).join(',');
        if (ids){
          const rg = await fetch(`${API_BASE}/playbooks/grades?trade_ids=${ids}`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
          const gj = await rg.json().catch(()=>({}));
          if (rg.ok && gj && gj.grades) setGradesMap(gj.grades);
        } else {
          setGradesMap({});
        }
      }catch{}
      setSelected([]);
    } catch (e:any) {
      setError(e.message || String(e));
    } finally { setLoading(false); }
  }

  useEffect(() => { if (token) { load(); } }, [token, activeFilters, symbol, account, startDate, endDate, sort, page, pageSize]);

  function handleApplyFilters(filterDsl: FilterDSL | null){
    setActiveFilters(filterDsl);
    setPage(1);
    const next = new URLSearchParams();
    if (symbol) next.set("symbol", symbol);
    if (account) next.set("account", account);
    if (startDate) next.set("start", startDate);
    if (endDate) next.set("end", endDate);
    if (sort) next.set("sort", sort);
    if (filterDsl) {
      next.set("filters", encodeURIComponent(JSON.stringify(filterDsl)));
    }
    router.push(`/trades?${next.toString()}`);
  }

  function handleRemoveFilterCondition(index: number){
    if (!activeFilters) return;
    const newConditions = activeFilters.conditions.filter((_, i) => i !== index);
    const newFilters = newConditions.length > 0 ? { ...activeFilters, conditions: newConditions } : null;
    handleApplyFilters(newFilters);
  }

  function handleClearAllFilters(){
    handleApplyFilters(null);
  }

  function applyFilters(){
    const next = new URLSearchParams();
    if (symbol) next.set("symbol", symbol);
    if (account) next.set("account", account);
    if (startDate) next.set("start", startDate);
    if (endDate) next.set("end", endDate);
    if (sort) next.set("sort", sort);
    if (activeFilters) {
      next.set("filters", encodeURIComponent(JSON.stringify(activeFilters)));
    }
    router.push(`/trades?${next.toString()}`);
    setPage(1);
    try{
      localStorage.setItem('trades_start', startDate);
      localStorage.setItem('trades_end', endDate);
      localStorage.setItem('trades_sort', sort);
      localStorage.setItem('trades_page_size', String(pageSize));
    }catch{}
  }

  function clearFilters(){
    setSymbol("");
    setAccount("");
    setStartDate("");
    setEndDate("");
    setSort("open_time_utc:desc");
    setActiveFilters(null);
    setPage(1);
    try{
      localStorage.removeItem('trades_start');
      localStorage.removeItem('trades_end');
      localStorage.removeItem('trades_sort');
    }catch{}
    router.push('/trades');
  }

  function toggleSort(field: string){
    setSort(prev => {
      const [f, dir] = (prev || '').split(':');
      const nextDir = f === field ? (dir === 'asc' ? 'desc' : 'asc') : 'asc';
      const next = `${field}:${nextDir}`;
      // push to URL and reload
      const nextParams = new URLSearchParams();
      if (symbol) nextParams.set('symbol', symbol);
      if (account) nextParams.set('account', account);
      if (startDate) nextParams.set('start', startDate);
      if (endDate) nextParams.set('end', endDate);
      nextParams.set('sort', next);
      router.push(`/trades?${nextParams.toString()}`);
      setPage(1);
      // force reload with new sort
      setTimeout(load, 0);
      return next;
    });
  }

  function sortIndicator(field: string){
    const [f, dir] = (sort || '').split(':');
    if (f !== field) return '';
    return dir === 'asc' ? ' ↑' : ' ↓';
  }

  async function addTrade(){
    if (!token){ setError("Login required"); return; }
    setAddBusy(true); setError(null);
    try{
      const normTime = (t:string) => t ? (t.length === 5 ? `${t}:00` : t) : '00:00:00';
      const open_ts = `${form.open_date} ${normTime(form.open_time)}`.trim();
      const close_ts = form.close_date ? `${form.close_date} ${normTime(form.close_time)}`.trim() : "";
      const payload: any = {
        account_name: form.account_name,
        symbol: form.symbol,
        side: form.side,
        open_time: open_ts,
        qty_units: parseFloat(form.qty_units||'0'),
        entry_price: parseFloat(form.entry_price||'0'),
        tz: form.tz || 'UTC',
      };
      if (close_ts) payload.close_time = close_ts;
      if (form.exit_price) payload.exit_price = parseFloat(form.exit_price);
      if (form.fees) payload.fees = parseFloat(form.fees);
      if (form.net_pnl) payload.net_pnl = parseFloat(form.net_pnl);
      if (form.notes_md) payload.notes_md = form.notes_md;
      const r = await fetch(`${API_BASE}/trades`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      });
      const j = await r.json().catch(()=>({}));
      if (!r.ok) throw new Error((j && j.detail) || `Add failed: ${r.status}`);
      setShowAdd(false);
      await load();
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setAddBusy(false); }
  }

  function fmtDate(iso?: string | null){
    if (!iso) return "-";
    try {
      const d = new Date(iso);
      const opts: Intl.DateTimeFormatOptions = {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
      };
      return new Intl.DateTimeFormat(undefined, displayTz ? { ...opts, timeZone: displayTz } : opts).format(d);
    } catch { return new Date(iso).toLocaleString(); }
  }

  const toggleSelect = (id:number, on:boolean) => {
    setSelected(prev => on ? Array.from(new Set([...prev, id])) : prev.filter(x=>x!==id));
  };

  const allChecked = items.length > 0 && selected.length === items.length;

  async function deleteSelected(){
    if (!token){ setError("Login required"); return; }
    if (!selected.length){ setError("Select at least one trade"); return; }
    const ok = confirm(`Delete ${selected.length} trade(s)? This cannot be undone.`);
    if (!ok) return;
    setLoading(true);
    try{
      const restores: any[] = [];
      for (const id of selected){
        const r = await fetch(`${API_BASE}/trades/${id}`, { method:'DELETE', headers:{ Authorization:`Bearer ${token}` }});
        if (!r.ok){
          const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`}));
          throw new Error(j.detail || `Delete failed: ${r.status}`);
        }
        const j = await r.json().catch(()=>({}));
        if (j && j.restore_payload){ restores.push(j.restore_payload); }
      }
      setLastDeleted(restores);
      await load();
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setLoading(false); }
  }

  function isoToYmdInTz(iso: string, tz?: string){
    try{
      const d = new Date(iso);
      const fmt = new Intl.DateTimeFormat('en-CA', { timeZone: tz && tz.trim() ? tz : 'UTC', year:'numeric', month:'2-digit', day:'2-digit' });
      return fmt.format(d); // YYYY-MM-DD
    }catch{ return iso.slice(0,10); }
  }

  async function openJournal(){
    if (selected.length !== 1){ setError("Select exactly one trade for journal"); return; }
    if (!token){ setError('Login required'); return; }
    const id = selected[0];
    const trade = items.find(t=>t.id===id);
    if (!trade){ setError('Trade not found in list'); return; }
    const ymd = isoToYmdInTz(trade.close_time_utc || trade.open_time_utc, displayTz || undefined);
    try{
      // Ensure journal exists (upsert)
      const r = await fetch(`${API_BASE}/journal/${ymd}`, { method:'PUT', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify({}) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `Journal upsert failed: ${r.status}`);
      const jid = j?.id;
      if (jid){
        // Link the selected trade
        await fetch(`${API_BASE}/journal/${jid}/trades`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify([id]) });
      }
      window.location.href = `/journal/${ymd}`;
    }catch(e:any){ setError(e.message || String(e)); }
  }

  async function saveJournal(){
    if (!token){ setError("Login required"); return; }
    if (selected.length !== 1){ setError("Select exactly one trade"); return; }
    const id = selected[0];
    try{
      const r = await fetch(`${API_BASE}/trades/${id}`, {
        method:'PATCH',
        headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` },
        body: JSON.stringify({ notes_md: journalText })
      });
      const j = await r.json().catch(()=>({}));
      if (!r.ok) throw new Error(j.detail || `Update failed: ${r.status}`);
      setJournalOpen(false);
      await load();
    }catch(e:any){ setError(e.message || String(e)); }
  }

  const rows = useMemo(() => items.map(t => (
    (!gradeFilter || (gradesMap[t.id] || '') === gradeFilter) && <tr key={t.id}>
      <td><input type="checkbox" checked={selected.includes(t.id)} onChange={e=>toggleSelect(t.id, e.target.checked)} /></td>
      <td>{t.account_name || '-'}</td>
      <td><a href={`/trades/${t.id}`}>{t.symbol || '-'}</a></td>
      <td>{t.side}</td>
      <td>{t.qty_units ?? '-'}</td>
      <td>{t.entry_price ?? '-'}</td>
      <td>{t.exit_price ?? '-'}</td>
      <td>{fmtDate(t.open_time_utc)}</td>
      <td>{fmtDate(t.close_time_utc)}</td>
      <td style={{color:(t.net_pnl ?? 0) >=0 ? 'green':'crimson'}}>{t.net_pnl ?? '-'}</td>
      <td>{gradesMap[t.id] || '-'}</td>
    </tr>
  )).filter(Boolean), [items, selected, displayTz, gradeFilter, gradesMap]);

  async function exportCsv(){
    if (!token){ setError('Login required'); return; }
    setLoading(true);
    try{
      const params = new URLSearchParams();
      if (symbol) params.set('symbol', symbol);
      if (account) params.set('account', account);
      if (startDate) params.set('start', startDate);
      if (endDate) params.set('end', endDate);
      if (sort) params.set('sort', sort);
      params.set('limit', '1000');
      params.set('offset', '0');
      const r = await fetch(`${API_BASE}/trades?${params.toString()}`, { headers: { Authorization: `Bearer ${token}` }});
      const j: Trade[] = await r.json();
      if (!r.ok) throw new Error((j as any)?.detail || `Export failed: ${r.status}`);
      const cols = ['account_name','symbol','side','qty_units','entry_price','exit_price','open_time_utc','close_time_utc','net_pnl','external_trade_id'];
      const header = cols.join(',');
      const lines = j.map(t => [
        t.account_name ?? '',
        t.symbol ?? '',
        t.side ?? '',
        t.qty_units ?? '',
        t.entry_price ?? '',
        t.exit_price ?? '',
        t.open_time_utc ?? '',
        t.close_time_utc ?? '',
        t.net_pnl ?? '',
        t.external_trade_id ?? '',
      ].map(v => String(v).replaceAll('"','""')).map(v => (/[,\n\r]/.test(v) ? `"${v}"` : v)).join(','));
      const csv = [header, ...lines].join('\n');
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `trades_export_${Date.now()}.csv`;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setLoading(false); }
  }

  if (!mounted){
    return (
      <main style={{maxWidth: 1000, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
        <h1>Trades</h1>
        <div style={{color:'#64748b'}}>Loading…</div>
      </main>
    );
  }

  return (
    <main style={{maxWidth: 1000, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>Trades</h1>
      {!token && (
        <div style={{margin:'8px 0', padding:'8px 12px', border:'1px solid #fde68a', background:'#fffbeb', color:'#92400e', borderRadius:8}}>
          Please <a href="/auth/login">sign in</a> to view your trades.
        </div>
      )}

      {/* Advanced Filter Builder */}
      {token && (
        <>
          <FilterBuilder onApply={handleApplyFilters} initialFilters={activeFilters || undefined} />
          <FilterChips
            filters={activeFilters}
            onRemoveCondition={handleRemoveFilterCondition}
            onClearAll={handleClearAllFilters}
          />
        </>
      )}

      <div style={{display:'flex', gap:8, margin:'8px 0', flexWrap:'wrap'}}>
        <div>
          <input list="symbol-list" placeholder="Symbol contains" value={symbol} onChange={e=>setSymbol(e.target.value)} />
          <datalist id="symbol-list">
            {symbols.map(s => (<option key={s} value={s} />))}
          </datalist>
        </div>
        <div>
          <input list="account-list" placeholder="Account contains" value={account} onChange={e=>setAccount(e.target.value)} />
          <datalist id="account-list">
            {accounts.map(a => (<option key={a.id} value={a.name} />))}
          </datalist>
        </div>
        <div style={{display:'flex', alignItems:'center', gap:6}}>
          <label>Grade:</label>
          <select value={gradeFilter} onChange={e=> setGradeFilter(e.target.value)}>
            <option value="">Any</option>
            {['A','B','C','D'].map(g => (<option key={g} value={g}>{g}</option>))}
          </select>
        </div>
        <input type="date" value={startDate} onChange={e=>setStartDate(e.target.value)} />
        <input type="date" value={endDate} onChange={e=>setEndDate(e.target.value)} />
        <div style={{display:'flex', alignItems:'center', gap:6}}>
          <span>Date presets:</span>
          <button type="button" onClick={()=>{ const d=new Date(); const ymd=d.toISOString().slice(0,10); setStartDate(ymd); setEndDate(ymd); setPage(1); applyFilters(); }}>Today</button>
          <button type="button" onClick={()=>{ const now=new Date(); const day=(now.getDay()+6)%7; const monday=new Date(now); monday.setDate(now.getDate()-day); const sunday=new Date(monday); sunday.setDate(monday.getDate()+6); const s=monday.toISOString().slice(0,10); const e=sunday.toISOString().slice(0,10); setStartDate(s); setEndDate(e); setPage(1); applyFilters(); }}>This Week</button>
          <button type="button" onClick={()=>{ const now=new Date(); const first=new Date(now.getFullYear(),now.getMonth(),1); const last=new Date(now.getFullYear(),now.getMonth()+1,0); const s=first.toISOString().slice(0,10); const e=last.toISOString().slice(0,10); setStartDate(s); setEndDate(e); setPage(1); applyFilters(); }}>This Month</button>
          <button type="button" onClick={clearFilters}>Clear All</button>
        </div>
        <select value={sort} onChange={e=>{ setSort(e.target.value); setPage(1); applyFilters(); }}>
          <option value="open_time_utc:desc">Open time ↓</option>
          <option value="open_time_utc:asc">Open time ↑</option>
          <option value="net_pnl:desc">Net PnL ↓</option>
          <option value="net_pnl:asc">Net PnL ↑</option>
          <option value="symbol:asc">Symbol A→Z</option>
          <option value="symbol:desc">Symbol Z→A</option>
          <option value="account:asc">Account A→Z</option>
          <option value="account:desc">Account Z→A</option>
        </select>
        <div style={{display:'flex', alignItems:'center', gap:6}}>
          <label>Per page:</label>
          <select value={pageSize} onChange={e=>{ const v=parseInt(e.target.value||'50',10); setPageSize(v); setPage(1); load(); }}>
            {[10,25,50,100].map(n=> (<option key={n} value={n}>{n}</option>))}
          </select>
        </div>
        <div style={{display:'flex', alignItems:'center', gap:6}}>
          <label>Display timezone:</label>
          <select
            value={displayTz}
            onChange={e=>{ const v = e.target.value; setDisplayTz(v); try{ localStorage.setItem("ej_display_tz", v);}catch{} }}
          >
            <option value="">Auto (Browser)</option>
            {[
              "UTC",
              "Australia/Sydney",
              "America/New_York",
              "Europe/London",
              "Asia/Singapore",
            ].map(z => (<option key={z} value={z}>{z}</option>))}
          </select>
        </div>
        <button onClick={applyFilters} disabled={loading}>{loading ? 'Loading…' : 'Apply'}</button>
        <button onClick={clearFilters} type="button">Clear Filters</button>
        <button onClick={()=>{ setShowAdd(s=>{
          const next = !s;
          if (next){
            // Prefill open date from selected day if provided
            const ymd = startDate || (new Date().toISOString().slice(0,10));
            setForm(f=>({ ...f, open_date: ymd }));
          }
          return next;
        }); }}>{showAdd ? 'Close' : 'Add Trade'}</button>
      </div>
      {showAdd && (
        <div style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12, margin:'8px 0'}}>
          <div style={{display:'grid', gridTemplateColumns:'repeat(3, minmax(0, 1fr))', gap:8}}>
            <div>
              <input list="account-list" placeholder="Account" value={form.account_name} onChange={e=>setForm(f=>({...f, account_name:e.target.value}))} />
            </div>
            <input list="symbol-list" placeholder="Symbol" value={form.symbol} onChange={e=>setForm(f=>({...f, symbol:e.target.value}))} />
            <select value={form.side} onChange={e=>setForm(f=>({...f, side:e.target.value}))}>
              <option>Buy</option>
              <option>Sell</option>
            </select>
            <div style={{display:'flex', gap:6}}>
              <input type="date" value={form.open_date} onChange={e=>setForm(f=>({...f, open_date:e.target.value}))} />
              <input type="time" value={form.open_time} onChange={e=>setForm(f=>({...f, open_time:e.target.value}))} />
            </div>
            <div style={{display:'flex', gap:6}}>
              <input type="date" value={form.close_date} onChange={e=>setForm(f=>({...f, close_date:e.target.value}))} />
              <input type="time" value={form.close_time} onChange={e=>setForm(f=>({...f, close_time:e.target.value}))} />
            </div>
            <input placeholder="Qty" value={form.qty_units} onChange={e=>setForm(f=>({...f, qty_units:e.target.value}))} />
            <input placeholder="Entry" value={form.entry_price} onChange={e=>setForm(f=>({...f, entry_price:e.target.value}))} />
            <input placeholder="Exit" value={form.exit_price} onChange={e=>setForm(f=>({...f, exit_price:e.target.value}))} />
            <input placeholder="Fees" value={form.fees} onChange={e=>setForm(f=>({...f, fees:e.target.value}))} />
            <input placeholder="Net PnL" value={form.net_pnl} onChange={e=>setForm(f=>({...f, net_pnl:e.target.value}))} />
            <input placeholder="Timezone (e.g., UTC, Australia/Sydney)" value={form.tz} onChange={e=>setForm(f=>({...f, tz:e.target.value}))} />
            <input placeholder="Notes" value={form.notes_md} onChange={e=>setForm(f=>({...f, notes_md:e.target.value}))} />
          </div>
          <div style={{marginTop:8}}>
            <button onClick={addTrade} disabled={addBusy}>{addBusy ? 'Saving…' : 'Save Trade'}</button>
          </div>
        </div>
      )}
      {error && <p style={{color:'crimson'}}>{error}</p>}
      <div style={{overflowX:'auto'}}>
        <table className="tbl" cellPadding={6} style={{width:'100%', borderCollapse:'collapse'}}>
          <thead style={{position:'sticky', top:0, zIndex:1}}>
            <tr className="tbl-head">
              <th><input type="checkbox" checked={allChecked} onChange={e=> setSelected(e.target.checked ? items.map(t=>t.id) : [])} /></th>
              <th style={{cursor:'pointer'}} onClick={()=>toggleSort('account')}>Account{sortIndicator('account')}</th>
              <th style={{cursor:'pointer'}} onClick={()=>toggleSort('symbol')}>Symbol{sortIndicator('symbol')}</th>
              <th>Side</th>
              <th style={{cursor:'pointer'}} onClick={()=>toggleSort('entry_price')}>Qty / Entry{sortIndicator('entry_price')}</th>
              <th>Exit</th>
              <th style={{cursor:'pointer'}} onClick={()=>toggleSort('open_time_utc')}>Open{sortIndicator('open_time_utc')}</th>
              <th style={{cursor:'pointer'}} onClick={()=>toggleSort('close_time_utc')}>Close{sortIndicator('close_time_utc')}</th>
              <th style={{cursor:'pointer'}} onClick={()=>toggleSort('net_pnl')}>Net PnL{sortIndicator('net_pnl')}</th>
              <th>Grade</th>
            </tr>
          </thead>
          <tbody>
            {rows}
            {!rows.length && (
              <tr><td colSpan={10} style={{textAlign:'center', color:'#64748b'}}>No trades</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div style={{display:'flex', gap:8, marginTop:8, flexWrap:'wrap', alignItems:'center'}}>
        <div style={{display:'flex', alignItems:'center', gap:8}}>
          <button onClick={()=>{ if (page>1){ setPage(p=>p-1); load(); } }} disabled={page<=1 || loading}>Prev</button>
          <span>Page {page}</span>
          <button onClick={()=>{ setPage(p=>p+1); load(); }} disabled={loading}>Next</button>
        </div>
        <button onClick={exportCsv} disabled={loading}>Export CSV</button>
        <button onClick={deleteSelected} disabled={!selected.length}>Delete Selected</button>
        <button onClick={openJournal} disabled={selected.length!==1}>Add Journal Entry</button>
        {loading && <span style={{color:'#64748b'}}>Loading…</span>}
      </div>
      {lastDeleted.length > 0 && (
        <div style={{marginTop:8, padding:'8px 12px', border:'1px solid #e5e7eb', background:'#f8fafc', borderRadius:8, display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <span>{lastDeleted.length} trade(s) deleted.</span>
          <button onClick={async ()=>{
            if (!token) { setError('Login required'); return; }
            try{
              for (const p of lastDeleted){
                const r = await fetch(`${API_BASE}/trades`, { method:'POST', headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` }, body: JSON.stringify(p) });
                if (!r.ok){ const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`})); throw new Error(j.detail || `Undo failed: ${r.status}`); }
              }
              setLastDeleted([]);
              await load();
            }catch(e:any){ setError(e.message || String(e)); }
          }}>Undo</button>
        </div>
      )}
      {/* Inline trade-notes journaling UI removed in favor of Daily Journal flow */}
    </main>
  );
}
