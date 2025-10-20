from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from .auth_utils import decode_token
from .db import get_db
from .models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Optional auth variant (no error on missing/invalid token)
oauth2_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    sub = decode_token(token)
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.email == sub).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return user

def get_optional_user(token: Optional[str] = Depends(oauth2_optional), db: Session = Depends(get_db)) -> Optional[User]:
    """Return the current user if a valid token is provided; otherwise None.

    This is useful for endpoints like CSV preview where personalisation (e.g.,
    applying a saved preset) is optional for unauthenticated users.
    """
    if not token:
        return None
    sub = decode_token(token)
    if not sub:
        return None
    user = db.query(User).filter(User.email == sub).first()
    if not user or not user.is_active:
        return None
    return user
