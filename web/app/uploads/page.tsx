"use client";
import { useEffect, useState } from "react";

type UploadRow = {
  id: number; filename: string; preset?: string | null; status: string; created_at?: string | null;
  inserted_count: number; updated_count: number; skipped_count: number; error_count: number;
};

export default function UploadsHistory(){
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const [rows, setRows] = useState<UploadRow[]>([]);
  const [token, setToken] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<number | null>(null);

  useEffect(() => { try { setToken(localStorage.getItem("ej_token") || ""); } catch{} }, []);

  async function load(){
    setError(null); setLoading(true);
    try{
      const r = await fetch(`${API_BASE}/uploads`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || `Failed: ${r.status}`);
      setRows(j);
    }catch(e:any){ setError(e.message || String(e)); }
    finally{ setLoading(false); }
  }

  useEffect(() => { load(); }, [token]);

  return (
    <main style={{maxWidth: 900, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>Imports</h1>
      {error && <p style={{color:'crimson'}}>{error}</p>}
      <div style={{overflowX:'auto'}}>
        <table cellPadding={6} style={{width:'100%', borderCollapse:'collapse'}}>
          <thead>
            <tr style={{background:'#f8fafc'}}>
              <th>When</th><th>File</th><th>Preset</th><th>TZ</th><th>Inserted</th><th>Updated</th><th>Skipped</th><th>Errors</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(u => (
              <tr key={u.id}>
                <td>{u.created_at ? new Date(u.created_at).toLocaleString() : '-'}</td>
                <td><a href={`/uploads/${u.id}`}>{u.filename}</a></td>
                <td>{u.preset || '-'}</td>
                <td>{(u as any).tz || '-'}</td>
                <td>{u.inserted_count}</td>
                <td>{u.updated_count}</td>
                <td>{u.skipped_count}</td>
                <td style={{color: u.error_count ? 'crimson' : '#0a0'}}>{u.error_count}</td>
                <td style={{display:'flex', gap:8}}>
                  {u.error_count > 0 && (
                    <button
                      onClick={async () => {
                        if (!token) { setError('Login required'); return; }
                        setDownloading(u.id);
                        try{
                          const r = await fetch(`${API_BASE}/uploads/${u.id}/errors.csv`, { headers: { Authorization: `Bearer ${token}` }});
                          if (!r.ok){
                            const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`}));
                            throw new Error(j.detail || `Download failed: ${r.status}`);
                          }
                          const blob = await r.blob();
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `upload-${u.id}-errors.csv`;
                          document.body.appendChild(a);
                          a.click();
                          a.remove();
                          URL.revokeObjectURL(url);
                        }catch(e:any){ setError(e.message || String(e)); }
                        finally{ setDownloading(null); }
                      }}
                      disabled={downloading === u.id}
                    >{downloading === u.id ? 'Downloading…' : 'Download errors'}</button>
                  )}
                  <button
                    onClick={async () => {
                      if (!token) { setError('Login required'); return; }
                      const ok = confirm('Delete this upload and its imported trades? This cannot be undone.');
                      if (!ok) return;
                      try{
                        const r = await fetch(`${API_BASE}/uploads/${u.id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` }});
                        if (!r.ok){
                          const j = await r.json().catch(()=>({detail:`HTTP ${r.status}`}));
                          throw new Error(j.detail || `Delete failed: ${r.status}`);
                        }
                        await load();
                      }catch(e:any){ setError(e.message || String(e)); }
                    }}
                  >Delete</button>
                </td>
              </tr>
            ))}
            {!rows.length && (
              <tr><td colSpan={9} style={{textAlign:'center', color:'#64748b'}}>No imports yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
