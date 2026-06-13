UC Transfer Chatbot backend

This backend is a Flask API around local UC transfer data, account state, saved conversations, and the chatbot model call.

It uses two SQLite databases.

`transfer.db` is public transfer data. It stores ASSIST agreement keys, raw agreement JSON, parsed articulation rows, and small seed facts.

`instance/app.db` is private app data. It stores users, sessions, account tokens, saved conversations, and saved messages. Do not commit it.

The JSON data under `data/` is for compact structured context that should not live in the LLM prompt by default. `data/transfer_requirements.json` currently stores IGETC and Cal-GETC facts.

From the repo root, set up the backend.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

If your shell does not support `source` or `cp`, use `.venv\Scripts\activate` and `copy .env.example .env`.

Set the required local env values in `backend/.env`.

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

`APP_BASE_URL` is used inside password reset and email verification links.

`FRONTEND_ORIGINS` controls which browser origins can make credentialed requests.

`SESSION_COOKIE_SECURE` should be `true` on HTTPS production deployments and `false` for local HTTP.

Run the backend from `backend/`.

```bash
python app.py
```

The API runs on `http://localhost:5000`.

The frontend runs separately and proxies `/api` to this backend.

Routes currently exposed by the backend:

- `GET /` confirms the backend is running.
- `GET /search` searches parsed articulation rows.
- `POST /chat` sends one message to the chatbot. Logged-in chats use saved database history. Guest chats must send browser-held history.
- `POST /auth/signup` creates an account and session.
- `POST /auth/login` creates a session.
- `POST /auth/logout` clears the current session.
- `GET /auth/me` returns the current user and CSRF token.
- `POST /auth/change-password` changes the logged-in user password.
- `POST /auth/email-verification/request` sends a verification link.
- `POST /auth/email-verification/confirm` consumes a verification token.
- `POST /auth/password-reset/request` sends a reset link when the account exists.
- `POST /auth/password-reset/confirm` consumes a reset token and clears existing sessions.
- `GET /conversations` lists saved chats for the logged-in user.
- `GET /conversations/<id>` loads one saved chat.
- `DELETE /conversations/<id>` deletes one saved chat owned by the logged-in user.

Write routes that change private app state require the session cookie and `X-CSRF-Token`.

`/chat` allows guest requests without cookies. If a valid session cookie is present, the request must include CSRF.

The model path keeps context short. It sends recent conversation messages plus a compact earlier-question index. It retrieves course rows only when the current user turn asks about courses. It retrieves IGETC / Cal-GETC JSON only when the user asks about general education or transfer requirements.

Set these on the Flask host for production:

- `AI_API_KEY`
- `USE_LLM7`
- `APP_BASE_URL`
- `FRONTEND_ORIGINS`
- `SESSION_COOKIE_SECURE`
- all `MAIL_*` values
- persistent storage for `backend/instance/app.db`
- persistent storage or deploy-time copy for `backend/transfer.db`
- HTTPS before secure cookies are enabled

If email fails, account creation and login still work. Password reset and email verification will return an email configuration error until SMTP is configured.

Run backend tests from the repo root with the backend environment activated.

```bash
python -m unittest backend.test_auth_routes
```
