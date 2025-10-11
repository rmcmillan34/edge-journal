from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .routes_auth import router as auth_router
from .routes_uploads import router as uploads_router
from .deps import get_current_user
from .models import User

app = FastAPI(title="Edge-Journal API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(uploads_router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "api", "version": "0.2.0"}

@app.get("/me")
def me(current: User = Depends(get_current_user)):
    return {"id": current.id, "email": current.email, "tz": current.tz}



