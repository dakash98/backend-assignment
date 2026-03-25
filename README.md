# IoT Data Service

FastAPI backend for user management, IoT data ingestion, historical/latest reads, and authenticated WebSocket streaming.

## Features

- JWT login with a configured admin user
- Protected REST APIs for user and IoT data management
- Authenticated WebSocket ingestion and subscription
- MongoDB persistence using Motor
- Validation for metric ranges, future timestamps, and active users
- In-memory rate limiting for login and REST APIs
- Automated tests for auth, REST, rate limiting, and WebSocket flow

## Setup

### Local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
uvicorn app.main:app --reload
```

The API starts on `http://localhost:8000`.

If MongoDB is not running locally, the app can still start for development and `/health` will work, but DB-backed endpoints will return `503 Database unavailable`.
Set `REQUIRE_DB_ON_STARTUP=true` if you want the service to fail fast instead.

HTTP rate limiting is enabled by default with separate limits for `POST /auth/login` and the rest of the REST API.
Tune it with `LOGIN_RATE_LIMIT_REQUESTS`, `LOGIN_RATE_LIMIT_WINDOW_SECONDS`, `API_RATE_LIMIT_REQUESTS`, and `API_RATE_LIMIT_WINDOW_SECONDS`.

Run the automated test suite with:

```bash
pytest
```

## Auth Flow

`POST /auth/login` is the only public API.

Example request:

```json
{
  "username": "admin",
  "password": "password"
}
```

Use the returned bearer token in REST requests:

```text
Authorization: Bearer <JWT_TOKEN>
```

For WebSockets, pass the token either as:

- Header: `Authorization: Bearer <JWT_TOKEN>`
- Query param: `/ws/ingest?token=<JWT_TOKEN>` or `/ws/subscribe?user_id=U1001&token=<JWT_TOKEN>`

Expired WebSocket tokens are closed with policy violation code `1008`.

## API Examples

Create user:

```bash
curl -X POST http://localhost:8000/users   -H "Authorization: Bearer <JWT_TOKEN>"   -H "Content-Type: application/json"   -d '{"user_id":"U1001","name":"Test User","status":"active"}'
```

Update user:

```bash
curl -X PUT http://localhost:8000/users/U1001   -H "Authorization: Bearer <JWT_TOKEN>"   -H "Content-Type: application/json"   -d '{"name":"Updated Name","status":"inactive"}'
```

Ingest data:

```bash
curl -X POST http://localhost:8000/iot/data   -H "Authorization: Bearer <JWT_TOKEN>"   -H "Content-Type: application/json"   -d '{"user_id":"U1001","metric_1":34.5,"metric_2":78,"metric_3":1,"timestamp":1710000000}'
```

Latest data:

```bash
curl -H "Authorization: Bearer <JWT_TOKEN>"   http://localhost:8000/users/U1001/iot/latest
```

History:

```bash
curl -H "Authorization: Bearer <JWT_TOKEN>"   http://localhost:8000/users/U1001/iot/history?limit=50
```

## WebSocket Examples

Subscribe:

```text
ws://localhost:8000/ws/subscribe?user_id=U1001&token=<JWT_TOKEN>
```

Ingest:

```text
ws://localhost:8000/ws/ingest?token=<JWT_TOKEN>
```

Incoming WS ingestion message:

```json
{
  "user_id": "U1001",
  "metric_1": 45.2,
  "metric_2": 88,
  "metric_3": 0,
  "timestamp": 1710000100
}
```

Example pushed event:

```json
{
  "event": "NEW_DATA",
  "data": {
    "user_id": "U1001",
    "metric_1": 45.2,
    "metric_2": 88,
    "metric_3": 0,
    "timestamp": 1710000100
  }
}
```

## Design Decisions

- FastAPI plus async Motor keeps REST and WebSocket handling in one async stack.
- The admin account is config-driven because the assignment requires login but not signup.
- Validation lives in Pydantic models plus service-layer user checks to keep handlers thin.
- A lightweight in-memory limiter protects login and REST endpoints without adding infrastructure dependencies.
- A lightweight connection manager broadcasts new data to subscribers and disconnects expired tokens.
