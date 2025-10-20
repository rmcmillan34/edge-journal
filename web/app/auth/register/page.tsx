"use client";
import { useState } from "react";

export default function RegisterPage() {
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
      // Register
      const r = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || `Register failed: ${r.status}`);

      // Auto-login
      const body = new URLSearchParams();
      body.set("username", email);
      body.set("password", password);
      const r2 = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const j2 = await r2.json();
      if (!r2.ok) throw new Error(j2.detail || `Login failed: ${r2.status}`);
      localStorage.setItem("ej_token", j2.access_token);
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
      <h1>Register</h1>
      <form onSubmit={onSubmit} style={{display:'grid', gap:8, marginTop:12}}>
        <input placeholder="Email" type="email" value={email} onChange={e=>setEmail(e.target.value)} required />
        <input placeholder="Password (min 8)" minLength={8} type="password" value={password} onChange={e=>setPassword(e.target.value)} required />
        <button type="submit" disabled={loading}>{loading ? 'Creating…' : 'Create account'}</button>
      </form>
      {error && <p style={{color:'crimson'}}>{error}</p>}
      <p style={{marginTop:8}}>
        Already have an account? <a href="/auth/login">Login</a>
      </p>
    </main>
  );
}

