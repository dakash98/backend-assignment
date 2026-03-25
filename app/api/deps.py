from fastapi import Header, HTTPException, Query, WebSocket, status

from app.core.security import decode_token
from app.db.mongodb import verify_database_connection


async def get_db():
    return await verify_database_connection()


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    return token


def get_current_subject(authorization: str | None = Header(default=None)) -> str:
    token = extract_bearer_token(authorization)
    payload = decode_token(token)
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return subject


async def get_websocket_auth(websocket: WebSocket, token: str | None = Query(default=None)) -> dict:
    raw_header = websocket.headers.get("authorization")
    if token:
        payload = decode_token(token)
    elif raw_header:
        payload = decode_token(extract_bearer_token(raw_header))
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    if not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return payload
