import time
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from pymongo.errors import PyMongoError

from app.api.deps import get_current_subject, get_db, get_websocket_auth
from app.db.mongodb import close_database, get_database
from app.core.config import get_settings
from app.core.rate_limit import api_rate_limit, login_rate_limit
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.iot import IoTDataIn, SubscribeEvent
from app.schemas.users import UserCreate, UserResponse, UserUpdate
from app.services.auth_service import AuthService
from app.services.iot_service import IoTService
from app.services.user_service import UserService
from app.services.ws_manager import WebSocketManager

router = APIRouter()
auth_service = AuthService()
ws_manager = WebSocketManager()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if app.state.initialize_db:
        db = get_database()
        try:
            await UserService(db).ensure_indexes()
            await IoTService(db).ensure_indexes()
        except PyMongoError as exc:
            if get_settings().require_db_on_startup:
                raise
            logger.warning("Skipping database initialization because MongoDB is unavailable: %s", exc)
    try:
        yield
    finally:
        await close_database()


@router.post("/auth/login", response_model=TokenResponse, tags=["auth"], dependencies=[Depends(login_rate_limit)])
async def login(payload: LoginRequest) -> TokenResponse:
    token = auth_service.login(payload.username, payload.password)
    return TokenResponse(access_token=token)


@router.post("/users", response_model=UserResponse, tags=["users"], dependencies=[Depends(api_rate_limit)])
async def create_user(
    payload: UserCreate,
    _: str = Depends(get_current_subject),
    db=Depends(get_db),
) -> dict:
    return await UserService(db).create_user(payload)


@router.put("/users/{user_id}", response_model=UserResponse, tags=["users"], dependencies=[Depends(api_rate_limit)])
async def update_user(
    user_id: str,
    payload: UserUpdate,
    _: str = Depends(get_current_subject),
    db=Depends(get_db),
) -> dict:
    return await UserService(db).update_user(user_id, payload)


@router.get("/users/{user_id}", response_model=UserResponse, tags=["users"], dependencies=[Depends(api_rate_limit)])
async def get_user(user_id: str, _: str = Depends(get_current_subject), db=Depends(get_db)) -> dict:
    return await UserService(db).get_user(user_id)


@router.post("/iot/data", response_model=IoTDataIn, tags=["iot"], dependencies=[Depends(api_rate_limit)])
async def ingest_data(payload: IoTDataIn, _: str = Depends(get_current_subject), db=Depends(get_db)) -> dict:
    await UserService(db).validate_active_user(payload.user_id)
    record = await IoTService(db).ingest(payload)
    await ws_manager.broadcast(payload.user_id, SubscribeEvent(data=IoTDataIn.model_validate(record)).model_dump())
    return record


@router.get("/users/{user_id}/iot/latest", response_model=IoTDataIn, tags=["iot"], dependencies=[Depends(api_rate_limit)])
async def get_latest_data(user_id: str, _: str = Depends(get_current_subject), db=Depends(get_db)) -> dict:
    await UserService(db).get_user(user_id)
    return await IoTService(db).latest(user_id)


@router.get("/users/{user_id}/iot/history", response_model=list[IoTDataIn], tags=["iot"], dependencies=[Depends(api_rate_limit)])
async def get_history_data(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    _: str = Depends(get_current_subject),
    db=Depends(get_db),
) -> list[dict]:
    await UserService(db).get_user(user_id)
    return await IoTService(db).history(user_id, limit)


@router.websocket("/ws/ingest")
async def websocket_ingest(websocket: WebSocket, db=Depends(get_db)) -> None:
    try:
        payload = await get_websocket_auth(websocket)
    except HTTPException:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        while True:
            if int(payload["exp"]) <= int(time.time()):
                await websocket.close(code=1008, reason="Token expired")
                break

            message = await websocket.receive_json()
            data = IoTDataIn.model_validate(message)
            await UserService(db).validate_active_user(data.user_id)
            record = await IoTService(db).ingest(data)
            await ws_manager.broadcast(data.user_id, SubscribeEvent(data=IoTDataIn.model_validate(record)).model_dump())
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.send_json({"error": str(exc)})


@router.websocket("/ws/subscribe")
async def websocket_subscribe(websocket: WebSocket, user_id: str, db=Depends(get_db)) -> None:
    try:
        payload = await get_websocket_auth(websocket)
        await UserService(db).get_user(user_id)
    except HTTPException:
        await websocket.close(code=1008)
        return

    await ws_manager.connect(user_id, websocket, int(payload["exp"]))
    try:
        while True:
            if int(payload["exp"]) <= int(time.time()):
                await websocket.close(code=1008, reason="Token expired")
                break
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(user_id, websocket)


def create_app(*, initialize_db: bool = True) -> FastAPI:
    app = FastAPI(title="IoT Data Service", version="0.1.0", lifespan=lifespan)
    app.state.initialize_db = initialize_db

    app.include_router(router)

    @app.get("/health", tags=["meta"])
    async def healthcheck() -> dict:
        return {"status": "ok"}

    return app
