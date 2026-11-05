# Employee Attendance & Leave Management API

Backend-only FastAPI service. No React frontend is included.

## Features
- JWT authentication with Admin and Employee roles.
- Admin employee creation, listing, updating and deactivation.
- Daily check-in/check-out with a unique employee/date constraint.
- Working-hour calculation after check-out.
- Leave requests with pending, approved and rejected states.
- Admin attendance and leave review endpoints.
- Date filters, pagination and role-protected dashboards.
- SQLite default; PostgreSQL supported with `DATABASE_URL`.
- Interactive Swagger documentation at `/docs`.

## Local setup
1. Python 3.11+ recommended.
2. `python -m venv .venv` then activate it.
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`; set a strong `SECRET_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD`.
5. Run `uvicorn app.main:app --reload`.

## Render
Build command: `pip install -r requirements.txt`
Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
Set `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and (recommended) PostgreSQL `DATABASE_URL` in Render Environment.
Do not commit `.env`. SQLite on an ephemeral web instance is not durable; use PostgreSQL for persistent production data.

## Login
`POST /auth/login` accepts form fields `username` (the email address) and `password`. Use the returned access token as `Authorization: Bearer <token>`.
The first startup creates an admin account using `ADMIN_EMAIL` and `ADMIN_PASSWORD`. Change defaults before deployment.

## API overview
- `POST /auth/login`, `GET /auth/me`
- Admin: `POST/GET /employees`, `PATCH /employees/{id}`
- Authenticated: `POST /attendance/check-in`, `POST /attendance/check-out`, `GET /attendance/me`
- Admin: `GET /attendance`
- Authenticated: `POST /leaves`, `GET /leaves/me`
- Admin: `GET /leaves`, `PATCH /leaves/{id}/review`
- Admin dashboard: `GET /dashboard/admin`
- Employee dashboard: `GET /dashboard/employee`

All timestamps use the server's local timezone-naive datetime convention; configure the hosting environment consistently.
