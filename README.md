# UC Transfer Chatbot

This project has:

- `backend/` (Flask API)
- `frontend/` (React + Vite app)


**quick note on storage policy**
- Transfer and articulation data belongs in `backend/transfer.db`.
- Private app data, including accounts, saved conversations, and chat messages, belongs in `backend/instance/app.db`.
- `backend/instance/` is included in gitignore and should not be used for public seed data.

## Prerequisites

- Python 3.10+ (recommended)
- Node.js 18+ (or newer LTS)
- `pnpm` installed globally

If you do not have `pnpm` yet:

```bash
npm install -g pnpm
```

## 1) Install Backend Requirements

From the project root:

```bash
cd backend
pip install -r requirements.txt
```

## 2) Configure the `.env` File

The backend needs an AI API key to work. From `backend/`, copy the example file to create your own `.env`:

```bash
cd backend
cp .env.example .env
```

Then open `.env` and add your API key.

We'll use [LLM7.io](https://llm7.io/) for the AI API key (it has a great free tier). To get a key:

1. Go to [https://llm7.io/](https://llm7.io/) and create an account.
2. On the dashboard, scroll down to **Manage API keys** and click **Add API key**.
3. Copy the generated key and paste it into your `.env` file as the value of `AI_API_KEY`.

Make sure `USE_LLM7=true` is set when using an LLM7.io key:

```bash
AI_API_KEY="your-key-here"
USE_LLM7=true
```

> Alternatively, you can use a default OpenAI API key. In that case, set `USE_LLM7=false` and use your OpenAI key as `AI_API_KEY`.

## 3) Install Frontend Requirements

In a second terminal (or after finishing backend setup):

```bash
cd frontend
pnpm i
```

## 4) Run the Backend

From `backend/`:

```bash
python app.py
```

Backend runs at: `http://localhost:5000`

## 5) Run the Frontend

From `frontend/`:

```bash
pnpm dev --open
```

Frontend runs at: `http://localhost:5173`

## Quick Start (Two Terminals)

Terminal 1 (backend):

```bash
cd backend
python app.py
```

Terminal 2 (frontend):

```bash
cd frontend
pnpm dev --open
```
