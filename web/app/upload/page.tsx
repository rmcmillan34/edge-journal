"use client";
import { useEffect, useMemo, useState } from "react";

type Mapping = Record<string, string>;

const CORE_FIELDS = [
  "Account","Symbol","Side","Open Time","Close Time",
  "Quantity","Entry Price","Exit Price","Fees","Net PnL",
  "ExternalTradeID","Notes",
] as const;

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [headers, setHeaders] = useState<string[]>([]);
  const [mapping, setMapping] = useState<Mapping>({});
  const [token, setToken] = useState<string>(()=>{ try{ return localStorage.getItem('ej_token') || ""; }catch{ return ""; } });
  const [mounted, setMounted] = useState(false);
  const [presetName, setPresetName] = useState<string>("");
  const [applyPresetOnPreview, setApplyPresetOnPreview] = useState<boolean>(true);
  const [accountName, setAccountName] = useState<string>("");
  const [accounts, setAccounts] = useState<{id:number; name:string}[]>([]);
  const [presets, setPresets] = useState<{id:number; name:string}[]>([]);
  const [tz, setTz] = useState<string>("UTC");
  const MAX_UPLOAD_MB = Number(process.env.NEXT_PUBLIC_MAX_UPLOAD_MB || 20);

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  useEffect(() => {
    try {
      const savedTz = localStorage.getItem("ej_tz") || "";
      if (savedTz) setTz(savedTz);
    } catch {}
    setMounted(true);
  }, []);

  useEffect(() => {
    async function loadAuthData(){
      if (!token) return;
      try {
        const [a, p] = await Promise.all([
          fetch(`${API_BASE}/accounts`, { headers: { Authorization: `Bearer ${token}` }}),
          fetch(`${API_BASE}/presets`, { headers: { Authorization: `Bearer ${token}` }}),
        ]);
        if (a.ok) {
          const aj = await a.json();
          setAccounts(aj || []);
        }
        if (p.ok) {
          const pj = await p.json();
          setPresets((pj || []).map((x:any)=>({id:x.id, name:x.name})));
        }
      } catch {}
    }
    loadAuthData();
  }, [token, API_BASE]);

  function updateMapping(field: string, header: string) {
    setMapping(m => ({ ...m, [field]: header }));
  }

  async function initialPreview(e: React.FormEvent) {
    e.preventDefault();
    setError(null); setResult(null);
    if (!file) { setError("Choose a CSV file first"); return; }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) { setError(`File exceeds limit of ${MAX_UPLOAD_MB} MB`); return; }
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await fetch(`${API_BASE}/uploads`, { method: "POST", body: fd });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || `Upload failed: ${r.status}`);
      setResult(j);
      setHeaders(j.headers || []);
      setMapping(j.mapping || {});
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  async function rePreview() {
    if (!file) { setError("Choose a CSV file first"); return; }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) { setError(`File exceeds limit of ${MAX_UPLOAD_MB} MB`); return; }
    setError(null);
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("mapping", JSON.stringify(mapping));
      if (applyPresetOnPreview && presetName) fd.append("preset_name", presetName);
      if (tz) fd.append("tz", tz);
      const r = await fetch(`${API_BASE}/uploads/preview`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: fd,
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || `Preview failed: ${r.status}`);
      setResult({ ...j, mapping: j.applied_mapping });
      // headers aren’t returned by /preview; keep existing
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  async function commit() {
    if (!file) { setError("Choose a CSV file first"); return; }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) { setError(`File exceeds limit of ${MAX_UPLOAD_MB} MB`); return; }
    setError(null);
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("mapping", JSON.stringify(mapping));
      if (presetName) fd.append("preset_name", presetName);
      if (accountName) fd.append("account_name", accountName);
      if (tz) fd.append("tz", tz);
      const r = await fetch(`${API_BASE}/uploads/commit`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: fd,
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || `Commit failed: ${r.status}`);
      setResult(j);
      const msg = `Imported: ${j.inserted || 0} inserted, ${j.updated || 0} updated, ${j.skipped || 0} skipped.`
      setFlash(msg);
      setTimeout(() => setFlash(null), 6000);
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  async function savePreset() {
    if (!token) { setError("Enter a bearer token to save presets"); return; }
    if (!presetName) { setError("Enter a preset name"); return; }
    setError(null);
    setLoading(true);
    try {
      const r = await fetch(`${API_BASE}/presets`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: presetName, headers, mapping }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || `Save preset failed: ${r.status}`);
      setResult((prev: any) => ({ ...prev, saved_preset: j }));
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  const mappingRows = useMemo(() => {
    if (!headers?.length) return null;
    return CORE_FIELDS.map((f) => (
      <div key={f} style={{display:'flex', gap:8, alignItems:'center'}}>
        <label style={{width:160}}>{f}</label>
        <select value={mapping[f] || ""} onChange={e => updateMapping(f, e.target.value)}>
          <option value="">—</option>
          {headers.map(h => (<option key={h} value={h}>{h}</option>))}
        </select>
      </div>
    ));
  }, [headers, mapping]);

  return (
    <main style={{maxWidth: 900, margin: '2rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>CSV Upload</h1>
      <p style={{color:'#555'}}>Preview, adjust mapping, and commit trades. API base <code>{API_BASE}</code>.</p>

      <form onSubmit={initialPreview} style={{display:'flex', gap:8, alignItems:'center', margin:'1rem 0'}}>
        <input type="file" accept=".csv" onChange={e => setFile(e.target.files?.[0] || null)} />
        <button type="submit" disabled={loading}>{loading ? 'Uploading…' : 'Initial Preview'}</button>
        <input placeholder="Bearer token (optional)" value={token} onChange={e=>setToken(e.target.value)} style={{flex:1}} />
      </form>
      {mounted && !token && (
        <div style={{marginBottom:8, padding:'8px 12px', border:'1px solid #fde68a', background:'#fffbeb', color:'#92400e', borderRadius:8}}>
          Tip: <a href="/auth/login">Sign in</a> to commit trades and save presets.
        </div>
      )}
      {error && <p style={{color:'crimson'}}>{error}</p>}
      {flash && (
        <div style={{marginTop:8, padding:'8px 12px', border:'1px solid #22c55e', background:'#ecfdf5', color:'#065f46', borderRadius:8}}>
          <span style={{marginRight:8}}>✓</span>{flash}
        </div>
      )}

      {result && (
        <div style={{marginTop:16, padding:12, border:'1px solid #ddd', borderRadius:8}}>
          <p><b>Detected preset:</b> {result.detected_preset ?? '-'}</p>
          {Boolean(presets.length) && (
            <div style={{display:'flex', gap:8, alignItems:'center', margin:'8px 0'}}>
              <label>Preset:</label>
              <input list="preset-list" placeholder="Type to search" value={presetName} onChange={e=>setPresetName(e.target.value)} />
              <datalist id="preset-list">
                {presets.map(p=> (<option key={p.id} value={p.name} />))}
              </datalist>
              <label style={{display:'inline-flex', alignItems:'center', gap:6}}>
                <input type="checkbox" checked={applyPresetOnPreview} onChange={e=>setApplyPresetOnPreview(e.target.checked)} />
                Apply on preview
              </label>
            </div>
          )}
          {result.plan && (
            <p><b>Rows:</b> total {result.plan.rows_total ?? result.plan.rows_valid ?? 0}{" "}
              {result.plan.rows_invalid != null && <>invalid {result.plan.rows_invalid}</>} 
            </p>
          )}
          {tz && (
            <p><b>Preview timezone:</b> {tz}</p>
          )}
          {headers?.length > 0 && (
            <div style={{display:'grid', gridTemplateColumns:'1fr 2fr', gap:8, alignItems:'center', marginTop:12}}>
              <div style={{gridColumn:'1 / span 2'}}><b>Mapping</b></div>
              <div style={{gridColumn:'1 / span 2', display:'flex', gap:8, alignItems:'center'}}>
                <label>Timezone:</label>
                <select value={tz} onChange={e=>{ setTz(e.target.value); try{ localStorage.setItem("ej_tz", e.target.value);}catch{} }}>
                  {[
                    "UTC",
                    "Australia/Sydney",
                    "America/New_York",
                    "Europe/London",
                    "Asia/Singapore",
                  ].map(z => (<option key={z} value={z}>{z}</option>))}
                </select>
              </div>
              <div style={{gridColumn:'1 / span 2', display:'grid', gap:8}}>
                {mappingRows}
              </div>
            </div>
          )}
          <div style={{display:'flex', gap:8, marginTop:12}}>
            <input placeholder="Preset name (optional)" value={presetName} onChange={e=>setPresetName(e.target.value)} />
            {accounts.length ? (
              <select value={accountName} onChange={e=>setAccountName(e.target.value)}>
                <option value="">Default account (optional)</option>
                {accounts.map(a => (<option key={a.id} value={a.name}>{a.name}</option>))}
              </select>
            ): (
              <input placeholder="Default account (optional)" value={accountName} onChange={e=>setAccountName(e.target.value)} />
            )}
            <button onClick={rePreview} disabled={loading} type="button">Re‑Preview</button>
            <button onClick={commit} disabled={loading} type="button">Commit</button>
            <button onClick={savePreset} disabled={loading} type="button">Save Preset</button>
          </div>
          <details style={{marginTop:12}}>
            <summary>Raw response</summary>
            <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(result, null, 2)}</pre>
          </details>
        </div>
      )}
    </main>
  );
}
