# Edge‑Journal Web Build — Debug Context

This document captures neutral, factual context to troubleshoot a persistent Next.js build error in the web package. It includes environment details, error excerpts, relevant source snippets, and reproduction notes without proposing hypotheses or solutions.

## Scope
- App: `web/` (Next.js 14, TypeScript/TSX, React 18)
- Build environment: Docker (base `node:20-alpine`), `npm run build`
- Error location: pages under `web/app/…`, notably `app/trades/[id]/page.tsx` and previously `app/journal/[date]/page.tsx`

## Environment
- Node: `node:20-alpine` (Docker)
- Next.js: `14.2.5`
- React: `18.3.1`
- TypeScript: `^5.5.4`
- tsconfig (key options):
  - `"jsx": "preserve"`
  - `"moduleResolution": "bundler"`
  - `"strictNullChecks": true`
- next.config.js (key options):
  - `output: 'standalone'`
  - `reactStrictMode: true`

## Build Command
- In Dockerfile (web): `RUN npm run build`
- In container: `next build`

## Representative Error Excerpts

From `results.txt` (latest runs):

```
./app/trades/[id]/page.tsx
Error:
  x Unexpected token `main`. Expected jsx identifier
     ,-[ /app/app/trades/[id]/page.tsx:360:1]
  360 |   }
  361 |
  362 |   return <main style={{maxWidth: 1000, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
      :          ^^^^
  363 |       <h1>Trade #{params.id}</h1>
  364 |       {error && <p style={{color:'crimson'}}>{error}</p>}
  365 |       {!data ? <p>Loading…</p> : (
      `----
Caused by:
  Syntax Error
Import trace for requested module:
  ./app/trades/[id]/page.tsx
```

Earlier runs also showed on `app/journal/[date]/page.tsx`:

```
./app/journal/[date]/page.tsx
Error:
  x Expression expected
     ,-[ /app/app/journal/[date]/page.tsx:358:1]
  358 |   return <>
      :          ^
...
  x Expected ',', got '{'
     ,-[ /app/app/journal/[date]/page.tsx:463:1]
  463 |                 <div style={{fontWeight:600}}>Previous Checklists</div>
      :                  ^
```

Note: In multiple logs the caret (`^^^^`) rendered near `main` (and sometimes near `fontFamily`) at the first JSX tag following a `return` statement.

## Relevant Source Snippets

Working baseline (Home page): `web/app/page.tsx`

```tsx
export default function Home(){
  return (
    <main style={{maxWidth:720, margin:'4rem auto', fontFamily:'system-ui,sans-serif'}}>
      <h1>Edge-Journal</h1>
      <p>Blank scaffold is live.</p>
    </main>
  );
}
```

Failing location (trades): `web/app/trades/[id]/page.tsx` around the reported line:

```tsx
// … precedes: handlers including React.DragEvent<HTMLDivElement> usage

// Current structure used during troubleshooting (excerpt)
const page = (
  <main style={{maxWidth: 1000, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
    <h1>Trade #{params.id}</h1>
    {error && <p style={{color:'crimson'}}>{error}</p>}
    {!data ? <p>Loading…</p> : (
      <div>
        {/* … content … */}
      </div>
    )}
  </main>
);
return page;
```

Previously affected location (journal): `web/app/journal/[date]/page.tsx` around the return:

```tsx
return (
  <React.Fragment>
    <main style={{maxWidth: 1000, margin:'2rem auto', fontFamily:'system-ui,sans-serif'}}>
      {/* … content … */}
    </main>
  </React.Fragment>
);
```

## Repository Files Potentially Relevant
- `web/tsconfig.json`: `jsx: preserve`, `moduleResolution: bundler`
- `web/next.config.js`: `output: 'standalone'`, `reactStrictMode: true`
- `web/Dockerfile`: builds on `node:20-alpine`, runs `npm ci` then `npm run build`
- `web/app/layout.tsx`: sets global fonts and `font-family` CSS variables

## Reproduction Notes
1) Build the web image:
   - `docker compose build --no-cache --progress=plain web`
2) Run the build inside image:
   - `npm run build`
3) Error appears during Next.js compilation; import trace shows the page file being compiled.

## Observed Build Logs (Docker)
- Cache behavior: some runs showed `COPY . .` as `CACHED` vs. fresh copy.
- Node and npm deprecation warnings observed (e.g., eslint version), not correlated with the error.

## Additional Context
- The error consistently references the first JSX element after a `return` in the affected page files.
- A working page (`web/app/page.tsx`) uses a similar inline style object with `fontFamily: 'system-ui,sans-serif'` and compiles successfully.
- Both affected pages include TypeScript generic annotations elsewhere (e.g., `React.DragEvent<HTMLDivElement>`), asynchronous handlers, and inline JSX props; these are noted here for context only.

## Artifacts Availability
- Full error output is captured in `results.txt` at repo root.
- Relevant page sources:
  - `web/app/trades/[id]/page.tsx`
  - `web/app/journal/[date]/page.tsx`
- Configs:
  - `web/tsconfig.json`
  - `web/next.config.js`
  - `web/package.json`
  - `web/Dockerfile`

## Goal
Provide enough neutral context so a reader (or tool) can reproduce and systematically diagnose the build error without being steered toward any particular explanation or fix.

