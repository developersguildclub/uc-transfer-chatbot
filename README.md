UC Transfer Chatbot

This is a React + Flask chatbot for UC transfer planning.

The frontend lives in `frontend/`.

The backend lives in `backend/`.

Transfer and articulation data lives in `backend/transfer.db` and JSON files under `backend/data/`.

Private app data lives in `backend/instance/app.db`. That includes accounts, sessions, saved chats, and saved messages. Keep `backend/instance/` out of git.

The app currently supports this set of flows.

- course articulation lookup from local ASSIST-derived data
- IGETC and Cal-GETC context from JSON data
- short, evidence-backed chatbot responses
- guest chats in browser state
- saved chats for logged-in users
- signup, login, logout
- password change
- password reset by email
- email verification by email
- account management from the app header

Use two terminals for local development.

Run this in Terminal 1.

```bash
cd /Users/nadathurv/Downloads/GitHub/uc-transfer-chatbot/backend && source "$HOME/Documents/uv_global_venv/bin/activate" && python app.py
```

Run this in Terminal 2.

```bash
cd /Users/nadathurv/Downloads/GitHub/uc-transfer-chatbot/frontend && npx pnpm@latest install && npx pnpm@latest dev
```

Open `http://localhost:5173`.

The frontend proxies `/api` to `http://localhost:5000`.

Create `backend/.env` from `backend/.env.example`.

Set these in `backend/.env` for local work.

```bash
AI_API_KEY="your-key"
USE_LLM7=true
APP_BASE_URL="http://localhost:5173"
FRONTEND_ORIGINS="http://localhost:5173"
SESSION_COOKIE_SECURE=false
```

Email features need SMTP config.

```bash
MAIL_HOST="smtp.example.com"
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME="smtp-user"
MAIL_PASSWORD="smtp-password"
MAIL_FROM="UC Transfer Chatbot <no-reply@example.com>"
```

For production, set `APP_BASE_URL` to the frontend URL. Set `FRONTEND_ORIGINS` to the exact frontend origin. Set `SESSION_COOKIE_SECURE=true` when serving over HTTPS.

These are the usual checks before opening a PR.

```bash
cd /Users/nadathurv/Downloads/GitHub/uc-transfer-chatbot/frontend && npx pnpm@latest lint && npx pnpm@latest build
```

```bash
cd /Users/nadathurv/Downloads/GitHub/uc-transfer-chatbot/backend && source "$HOME/Documents/uv_global_venv/bin/activate" && python -m unittest backend.test_auth_routes
```

If port `5000` is busy on macOS, inspect it before killing anything. AirPlay Receiver / Control Center can bind that port.
