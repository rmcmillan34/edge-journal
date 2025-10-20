"use client";
import { useState } from "react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const body = new URLSearchParams();
      body.set("username", email);
      body.set("password", password);
      const r = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || `Login failed: ${r.status}`);
      const token = j.access_token as string;
      localStorage.setItem("ej_token", token);
      localStorage.setItem("ej_email", email);
      window.location.href = "/upload";
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{maxWidth:480, margin:'3rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>Login</h1>
      <form onSubmit={onSubmit} style={{display:'grid', gap:8, marginTop:12}}>
        <input placeholder="Email" type="email" value={email} onChange={e=>setEmail(e.target.value)} required />
        <input placeholder="Password" type="password" value={password} onChange={e=>setPassword(e.target.value)} required />
        <button type="submit" disabled={loading}>{loading ? 'Signing in…' : 'Sign in'}</button>
      </form>
      {error && <p style={{color:'crimson'}}>{error}</p>}
      <p style={{marginTop:8}}>
        No account? <a href="/auth/register">Register</a>
      </p>
    </main>
  );
}

