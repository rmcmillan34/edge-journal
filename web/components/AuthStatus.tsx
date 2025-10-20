"use client";
import { useEffect, useState } from "react";

export default function AuthStatus(){
  const [email, setEmail] = useState<string>("");
  const [token, setToken] = useState<string>("");

  useEffect(() => {
    try {
      setToken(localStorage.getItem("ej_token") || "");
      setEmail(localStorage.getItem("ej_email") || "");
    } catch {}
  }, []);

  function logout(){
    try {
      localStorage.removeItem("ej_token");
      localStorage.removeItem("ej_email");
    } catch {}
    window.location.reload();
  }

  return (
    <div style={{display:'flex', gap:12, alignItems:'center', fontSize:14}}>
      {token ? (
        <>
          <span>Signed in{email ? ` as ${email}` : ""}</span>
          <button onClick={logout}>Logout</button>
        </>
      ) : (
        <>
          <a href="/auth/login">Login</a>
          <a href="/auth/register">Register</a>
        </>
      )}
    </div>
  );
}

