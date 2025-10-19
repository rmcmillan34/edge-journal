export default function Home(){
  return (
    <main style={{maxWidth:720,margin:'4rem auto',fontFamily:'system-ui,sans-serif'}}>
      <h1>Edge-Journal</h1>
      <p>Blank scaffold is live.</p>
      <ul>
        <li>API health: <code>GET http://localhost:8000/health</code></li>
        <li><a href="/upload">CSV Upload</a></li>
        <li><a href="/auth/login">Login</a> · <a href="/auth/register">Register</a></li>
      </ul>
    </main>
  );
}
