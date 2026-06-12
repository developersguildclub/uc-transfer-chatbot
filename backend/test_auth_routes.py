import importlib
import json
import pathlib
import sys
import tempfile
import unittest

BACKEND_DIR = pathlib.Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def stream_events(response):
    events = {}
    body = response.get_data(as_text=True)
    for block in body.split("\n\n"):
        lines = block.splitlines()
        if len(lines) < 2:
            continue

        event = lines[0].split(": ", 1)[1]
        data = json.loads(lines[1].split(": ", 1)[1])
        events[event] = data

    return events


class AuthRoutesTest(unittest.TestCase):
    def test_guest_chat_and_saved_chat_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = importlib.import_module("database")
            root = pathlib.Path(tmp)
            database.TRANSFER_DB_PATH = root / "transfer.db"
            database.DB_PATH = database.TRANSFER_DB_PATH
            database.APP_DB_PATH = root / "app.db"

            app_module = importlib.import_module("app")
            app_module.get_ai_response = lambda messages: f"reply to {len(messages)} message(s)"

            origin = {"Origin": "http://localhost:5173"}
            guest = app_module.app.test_client()

            response = guest.post("/chat", json={"message": "hello"}, headers=origin)
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(stream_events(response)["message_start"]["conversation_id"])

            response = guest.get("/conversations")
            self.assertEqual(response.status_code, 401)

            user = app_module.app.test_client()
            response = user.post(
                "/auth/signup",
                json={"email": "route-test@example.com", "password": "password123"},
                headers=origin,
            )
            self.assertEqual(response.status_code, 201)
            csrf_token = response.get_json()["csrfToken"]

            response = user.post("/chat", json={"message": "save this"}, headers=origin)
            self.assertEqual(response.status_code, 403)

            response = user.post(
                "/chat",
                json={"message": "save this"},
                headers={"Origin": "http://localhost:5173", "X-CSRF-Token": csrf_token},
            )
            self.assertEqual(response.status_code, 200)
            conversation_id = stream_events(response)["message_start"]["conversation_id"]

            response = user.post(
                "/chat",
                json={"message": "bad id", "conversation_id": True},
                headers={"Origin": "http://localhost:5173", "X-CSRF-Token": csrf_token},
            )
            self.assertEqual(response.status_code, 400)

            response = user.get("/conversations")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()["conversations"][0]["id"], conversation_id)

            response = user.get(f"/conversations/{conversation_id}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                [message["role"] for message in response.get_json()["messages"]],
                ["user", "assistant"],
            )
