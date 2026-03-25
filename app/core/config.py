from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "IoT Data Service"
    mongodb_uri: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URI")
    mongodb_database: str = Field(default="iot_service", alias="MONGODB_DATABASE")
    mongodb_server_selection_timeout_ms: int = Field(
        default=2000,
        alias="MONGODB_SERVER_SELECTION_TIMEOUT_MS",
    )
    require_db_on_startup: bool = Field(default=False, alias="REQUIRE_DB_ON_STARTUP")
    login_rate_limit_requests: int = Field(default=5, alias="LOGIN_RATE_LIMIT_REQUESTS")
    login_rate_limit_window_seconds: int = Field(default=60, alias="LOGIN_RATE_LIMIT_WINDOW_SECONDS")
    api_rate_limit_requests: int = Field(default=60, alias="API_RATE_LIMIT_REQUESTS")
    api_rate_limit_window_seconds: int = Field(default=60, alias="API_RATE_LIMIT_WINDOW_SECONDS")
    jwt_secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="password", alias="ADMIN_PASSWORD")


@lru_cache
def get_settings() -> Settings:
    return Settings()
