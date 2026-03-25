from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash, verify_password


class AuthService:
    def __init__(self) -> None:
        settings = get_settings()
        self._username = settings.admin_username
        self._hashed_password = get_password_hash(settings.admin_password)

    def login(self, username: str, password: str) -> str:
        if username != self._username or not verify_password(password, self._hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return create_access_token(subject=username)
