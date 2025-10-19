from fastapi import FastAPI, Depends
import os
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
import pathlib
from fastapi.middleware.cors import CORSMiddleware
from .routes_auth import router as auth_router
from .routes_uploads import router as uploads_router
from .routes_presets import router as presets_router
from .routes_accounts import router as accounts_router
from .routes_trades import router as trades_router
from .routes_metrics import router as metrics_router
from .routes_journal import router as journal_router
from .routes_templates import router as templates_router
from .deps import get_current_user
from .models import User
from .version import get_version

app = FastAPI(title="Edge-Journal API", version=get_version())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(uploads_router)
app.include_router(presets_router)
app.include_router(accounts_router)
app.include_router(trades_router)
app.include_router(metrics_router)
app.include_router(journal_router)
app.include_router(templates_router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "api", "version": get_version()}

@app.get("/version")
def version():
    return {"version": get_version()}

@app.get("/me")
def me(current: User = Depends(get_current_user)):
    return {"id": current.id, "email": current.email, "tz": current.tz}


@app.on_event("startup")
def _auto_migrate_dev():
    if os.environ.get("ENV") == "dev":
        try:
            here = pathlib.Path(__file__).resolve().parent
            cfg_path = here.parent / "alembic.ini"
            cfg = AlembicConfig(str(cfg_path))
            # DATABASE_URL is read by env.py; nothing to set if env is present
            alembic_command.upgrade(cfg, "head")
            print("[alembic] upgrade head executed on startup (dev)")
        except Exception as e:
            # Don't crash app on migration error in dev; just log
            print(f"[alembic] startup migration skipped/failed: {e}")
