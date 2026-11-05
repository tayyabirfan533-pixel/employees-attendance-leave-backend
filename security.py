from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac
from secrets import token_bytes
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Employee

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(password: str) -> str:
    salt = token_bytes(16)
    digest = pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return salt.hex() + "$" + digest.hex()

def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        digest = pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 210_000)
        return digest.hex() == digest_hex
    except Exception:
        return False

def create_access_token(employee: Employee) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(employee.id), "role": employee.role, "exp": expire}, settings.secret_key, algorithm="HS256")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Employee:
    error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = int(payload.get("sub", ""))
    except Exception:
        raise error
    user = db.get(Employee, user_id)
    if not user or not user.is_active:
        raise error
    return user

def require_admin(user: Employee = Depends(get_current_user)) -> Employee:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
