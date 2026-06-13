UC Transfer Chatbot

This is a React + Vite frontend and Flask backend for UC transfer planning.

Transfer and articulation data lives in `backend/transfer.db` and JSON files under `backend/data/`.

Private app data lives in `backend/instance/app.db`. That includes accounts, sessions, saved chats, and saved messages. Keep `backend/instance/` out of git.

The frontend lives in `frontend/`. The backend lives in `backend/`.

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

You need Python 3.10+, Node.js 18+, and npm. You do not need pnpm installed globally because the commands use `npx pnpm@latest`.

```bash
git clone https://github.com/developersguildclub/uc-transfer-chatbot.git
cd uc-transfer-chatbot

cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

If your shell does not support `source` or `cp`, use `.venv\Scripts\activate` and `copy .env.example .env`.

Set the required backend env values in `backend/.env`.

```bash
AI_API_KEY="your-key"
USE_LLM7=true
APP_BASE_URL="http://localhost:5173"
FRONTEND_ORIGINS="http://localhost:5173"
SESSION_COOKIE_SECURE=false
```

Email is optional for basic local chat. Password reset and email verification need SMTP values.

```bash
MAIL_HOST="smtp.example.com"
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME="smtp-user"
MAIL_PASSWORD="smtp-password"
MAIL_FROM="UC Transfer Chatbot <no-reply@example.com>"
```

Run the backend from `backend/` and leave that terminal open.

```bash
python app.py
```

The backend runs at `http://localhost:5000`. In a second terminal from the repo root, run the frontend.

```bash
cd frontend
npx pnpm@latest install
npx pnpm@latest dev
```

Open `http://localhost:5173`.

The frontend proxies `/api` to the backend on port `5000`.

For production, set `APP_BASE_URL` to the deployed frontend URL. Set `FRONTEND_ORIGINS` to the exact frontend origin. Set `SESSION_COOKIE_SECURE=true` when serving over HTTPS.

Before opening a PR, run the frontend checks.

```bash
cd frontend
npx pnpm@latest lint
npx pnpm@latest build
```

Run backend tests from the repo root with the backend environment activated.

```bash
python -m unittest backend.test_auth_routes
```

If port `5000` is busy, inspect it before killing anything.
