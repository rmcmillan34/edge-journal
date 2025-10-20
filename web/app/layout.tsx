"use client";
import AuthStatus from "../components/AuthStatus";
import Toaster from "../components/Toaster";
import { useEffect, useState } from "react";

export default function RootLayout({ children }:{children:React.ReactNode}){
  const [theme, setTheme] = useState<'light'|'dark'>(()=>{
    if (typeof window === 'undefined') return 'dark';
    try{
      const saved = localStorage.getItem('ej_theme');
      if (saved === 'light' || saved === 'dark') return saved as any;
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      return prefersDark ? 'dark' : 'light';
    }catch{ return 'dark'; }
  });

  useEffect(()=>{
    try{
      document.documentElement.classList.toggle('dark', theme === 'dark');
      localStorage.setItem('ej_theme', theme);
    }catch{}
  }, [theme]);

  return (
    <html lang='en'>
      <head>
        <script dangerouslySetInnerHTML={{__html:`(function(){try{var s=localStorage.getItem('ej_theme');var d=(s==='dark')||(!s&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches);if(d){document.documentElement.classList.add('dark');}else{document.documentElement.classList.remove('dark');}}catch(e){document.documentElement.classList.add('dark');}})();`}} />
        <link rel="preload" as="font" type="font/ttf" href="/fonts/IosevkaNerdFont-Regular.ttf" crossOrigin="anonymous" />
        <link rel="preload" as="font" type="font/ttf" href="/fonts/IosevkaNerdFont-Bold.ttf" crossOrigin="anonymous" />
        <style dangerouslySetInnerHTML={{__html: `
          :root{
            --app-font: 'Iosevka Nerd Font', 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'CaskaydiaCove Nerd Font', 'Symbols Nerd Font', 'Nerd Font', 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
            --ctp-rosewater:#f5e0dc; --ctp-flamingo:#f2cdcd; --ctp-pink:#f5c2e7; --ctp-mauve:#cba6f7;
            --ctp-red:#f38ba8; --ctp-maroon:#eba0ac; --ctp-peach:#fab387; --ctp-yellow:#f9e2af;
            --ctp-green:#a6e3a1; --ctp-teal:#94e2d5; --ctp-sky:#89dceb; --ctp-sapphire:#74c7ec;
            --ctp-blue:#89b4fa; --ctp-lavender:#b4befe; --ctp-text:#cdd6f4; --ctp-subtext1:#bac2de; --ctp-subtext0:#a6adc8;
            --ctp-overlay2:#9399b2; --ctp-overlay1:#7f849c; --ctp-overlay0:#6c7086; --ctp-surface2:#585b70; --ctp-surface1:#45475a; --ctp-surface0:#313244;
            --ctp-base:#1e1e2e; --ctp-mantle:#181825; --ctp-crust:#11111b;
          }
          /* Prefer locally installed Nerd Fonts if present */
          @font-face { font-family: 'Iosevka Nerd Font'; src: local('Iosevka Nerd Font'), local('Iosevka NF'), url('/fonts/IosevkaNerdFont-Regular.ttf') format('truetype'); font-weight: 100 900; font-style: normal; font-display: swap; }
          @font-face { font-family: 'FiraCode Nerd Font'; src: local('FiraCode Nerd Font'), local('Fira Code Nerd Font'), local('FiraCode NF'); font-weight: 300 700; font-style: normal; font-display: swap; }
          @font-face { font-family: 'CaskaydiaCove Nerd Font'; src: local('CaskaydiaCove Nerd Font'), local('Cascadia Code NF'), local('CaskaydiaCove NF'); font-weight: 300 700; font-style: normal; font-display: swap; }
          /* explicit bold face fallback */
          @font-face { font-family: 'Iosevka Nerd Font'; src: local('Iosevka Nerd Font'), url('/fonts/IosevkaNerdFont-Bold.ttf') format('truetype'); font-weight: 700; font-style: normal; font-display: swap; }

          body, main, input, select, textarea, button, code, pre, .topnav { font-family: var(--app-font) !important; }
          .dark, .dark body{ background: var(--ctp-base); color: var(--ctp-text); }
          .dark body{ background: var(--ctp-base); color: var(--ctp-text); }
          .dark a{ color: var(--ctp-blue); }
          .dark .topnav{ border-bottom-color: var(--ctp-surface1) !important; }
          .dark input, .dark select, .dark textarea{ background: var(--ctp-surface0); color: var(--ctp-text); border:1px solid var(--ctp-surface2); }
          .dark button{ background: var(--ctp-surface1); color: var(--ctp-text); border:1px solid var(--ctp-surface2); }
          .dark button:hover{ background: var(--ctp-surface2); }
          .dark *{ scrollbar-color: var(--ctp-surface2) var(--ctp-base); }
          .dark ::selection{ background: var(--ctp-sapphire); color: var(--ctp-crust); }
          /* Attempt to neutralize hardcoded light borders */
          .dark *{ border-color: var(--ctp-surface1) !important; }

          /* Calendar theming */
          .dark .cal-grid{ border-color: var(--ctp-surface1) !important; }
          .dark .cal-weekhead{ background: var(--ctp-surface1) !important; color: var(--ctp-subtext1) !important; border-right-color: var(--ctp-surface1) !important; }
          .dark .cal-cell{ background: var(--ctp-surface0) !important; color: var(--ctp-text) !important; }
          .dark .cal-cell.pos{ --cal-day-bg: rgba(166,227,161,0.14) !important; --cal-badge-bg: rgba(166,227,161,0.22) !important; --cal-day-color: var(--ctp-green) !important; }
          .dark .cal-cell.neg{ --cal-day-bg: rgba(243,139,168,0.14) !important; --cal-badge-bg: rgba(243,139,168,0.22) !important; --cal-day-color: var(--ctp-red) !important; }
          .dark .cal-cell{ --cal-day-bg: var(--ctp-surface0) !important; }
          .dark .cal-cell .pnl-badge{ background: var(--cal-badge-bg) !important; color: var(--cal-day-color) !important; }

          /* Tables */
          .tbl-head { background: #f1f5f9; color: #334155; }
          .tbl-head th { font-weight: 600; }
          .dark .tbl-head { background: var(--ctp-surface1) !important; color: var(--ctp-subtext1) !important; }

          /* Apply zebra + hover to all app tables by default (opt-out via .no-zebra) */
          table:not(.no-zebra) tbody tr:nth-child(even){ background: #f8fafc; }
          table:not(.no-zebra) tbody tr:hover{ background: #eef2f7; }
          .dark table:not(.no-zebra) tbody tr:nth-child(even){ background: var(--ctp-surface0) !important; }
          .dark table:not(.no-zebra) tbody tr:hover{ background: var(--ctp-surface1) !important; }
          /* Default header styling for tables without explicit .tbl-head */
          table:not(.no-zebra) thead tr { background: #f1f5f9; color: #334155; }
          table:not(.no-zebra) thead th { font-weight: 600; }
          .dark table:not(.no-zebra) thead tr { background: var(--ctp-surface1) !important; color: var(--ctp-subtext1) !important; }

          /* Notices */
          .dark .notice{ background: var(--ctp-surface1) !important; color: var(--ctp-text) !important; border-color: var(--ctp-surface2) !important; }
        `}} />
      </head>
      <body>
        
        <div className="topnav" style={{display:'flex', justifyContent:'space-between', alignItems:'center', padding:'8px 12px', borderBottom:'1px solid #eee'}}>
          <div style={{display:'flex', gap:12}}>
            <a href="/">Edge‑Journal</a>
            <a href="/dashboard">Dashboard</a>
            <a href="/upload">Upload</a>
            <a href="/uploads">Imports</a>
            <a href="/trades">Trades</a>
            <a href="/templates">Templates</a>
          </div>
          <div style={{display:'flex', alignItems:'center', gap:8}}>
            <button onClick={()=> setTheme(t => t==='dark' ? 'light' : 'dark')} title="Toggle theme" aria-label="Toggle theme">
              {theme === 'dark' ? '🌙 Mocha' : '☀️ Light'}
            </button>
            <AuthStatus />
          </div>
        </div>
        <Toaster />
        {children}
      </body>
    </html>
  );
}
