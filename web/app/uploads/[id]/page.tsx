"use client";
import { useEffect, useState } from "react";

type UploadDetail = {
  id: number; filename: string; preset?: string | null; tz?: string | null; status: string; created_at?: string | null;
  inserted_count: number; updated_count: number; skipped_count: number; error_count: number; errors?: {line:number; reason:string}[];
};

export default function UploadDetailPage({ params }:{ params: { id: string } }){
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const [token, setToken] = useState<string>("");
  const [data, setData] = useState<UploadDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => { try { setToken(localStorage.getItem("ej_token") || ""); } catch{} }, []);

  useEffect(() => { if (token) load(); }, [token]);

  async function load(){
    setError(null); setLoading(true);
    try{
      const r = await fetch(`${API_BASE}/uploads/${params.id}`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || `Failed: ${r.status}`);
      setData(j);
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setLoading(false); }
  }

  return (
    <main style={{maxWidth: 900, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>Upload #{params.id}</h1>
      {error && <p style={{color:'crimson'}}>{error}</p>}
      {!data ? (
        <p>{loading ? 'Loading…' : 'No data'}</p>
      ) : (
        <>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:8}}>
            <div><b>File:</b> {data.filename}</div>
            <div><b>Preset:</b> {data.preset || '-'}</div>
            <div><b>TZ:</b> {data.tz || '-'}</div>
            <div><b>When:</b> {data.created_at ? new Date(data.created_at).toLocaleString() : '-'}</div>
            <div><b>Inserted:</b> {data.inserted_count}</div>
            <div><b>Updated:</b> {data.updated_count}</div>
            <div><b>Skipped:</b> {data.skipped_count}</div>
            <div><b>Errors:</b> {data.error_count}</div>
          </div>
          <div style={{marginTop:12, display:'flex', gap:8}}>
            {data.error_count > 0 && (
              <button
                onClick={async () => {
                  if (!token) { setError('Login required'); return; }
                  setDownloading(true);
                  try{
                    const r = await fetch(`${API_BASE}/uploads/${params.id}/errors.csv`, { headers: { Authorization: `Bearer ${token}` }});
                    if (!r.ok){
                      const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`}));
                      throw new Error(j.detail || `Download failed: ${r.status}`);
                    }
                    const blob = await r.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `upload-${params.id}-errors.csv`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    URL.revokeObjectURL(url);
                  }catch(e:any){ setError(e.message || String(e)); }
                  finally{ setDownloading(false); }
                }}
                disabled={downloading}
              >{downloading ? 'Downloading…' : 'Download errors CSV'}</button>
            )}
          </div>
          {data.errors && data.errors.length > 0 && (
            <details style={{marginTop:12}}>
              <summary>Error lines</summary>
              <ul>
                {data.errors.map((e, i) => (
                  <li key={i}><code>line {e.line}</code>: {e.reason}</li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </main>
  );
}
