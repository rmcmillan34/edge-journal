import AuthStatus from "../components/AuthStatus";
import Toaster from "../components/Toaster";

export default function RootLayout({ children }:{children:React.ReactNode}){
  return (
    <html lang='en'>
      <body>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', padding:'8px 12px', borderBottom:'1px solid #eee'}}>
          <div style={{display:'flex', gap:12}}>
            <a href="/">Edge‑Journal</a>
            <a href="/dashboard">Dashboard</a>
            <a href="/upload">Upload</a>
            <a href="/uploads">Imports</a>
            <a href="/trades">Trades</a>
            <a href="/templates">Templates</a>
          </div>
          <AuthStatus />
        </div>
        <Toaster />
        {children}
      </body>
    </html>
  );
}
