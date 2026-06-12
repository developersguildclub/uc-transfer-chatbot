import importlib
import json
import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace

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
    def test_course_matching_uses_code_boundaries(self):
        model = importlib.import_module("model")

        self.assertEqual(
            model.first_mentioned(["ACCT 1A", "ACCT 1AH"], "does acct 1ah articulate?"),
            "ACCT 1AH",
        )
        self.assertEqual(
            model.first_mentioned(["ADMJ 1", "ADMJ 11"], "does admj 11 articulate?"),
            "ADMJ 11",
        )
        self.assertIsNone(model.first_mentioned(["ADMJ 1"], "does admj 11 articulate?"))

    def test_chat_history_question_does_not_reuse_stale_course_rows(self):
        model = importlib.import_module("model")
        calls = {}
        get_chat_model = model.get_chat_model
        get_valid_schools = model.get_valid_schools
        get_valid_major = model.get_valid_major
        get_valid_receiving_courses = model.get_valid_receiving_courses
        get_valid_cc_courses = model.get_valid_cc_courses
        search_articulations = model.search_articulations

        class ChatModel:
            def invoke(self, messages):
                calls["messages"] = messages
                return SimpleNamespace(content="ok")

        model.get_chat_model = lambda: ChatModel()
        model.get_valid_schools = lambda: ["University of California, Davis"]
        model.get_valid_major = lambda: ["Computer Science"]
        model.get_valid_receiving_courses = lambda: []
        model.get_valid_cc_courses = lambda: ["CIS 22C"]
        model.search_articulations = lambda **kwargs: self.fail(
            "chat history questions should not retrieve old course rows"
        )

        try:
            answer = model.get_ai_response(
                [
                    {"role": "user", "content": "list the uc colleges"},
                    {
                        "role": "assistant",
                        "content": "The UC colleges listed in the local data summary are...",
                    },
                    {"role": "user", "content": "Does CIS 22C articulate?"},
                    {
                        "role": "assistant",
                        "content": "Yes, local data has matches for CIS 22C.",
                    },
                    {
                        "role": "user",
                        "content": "what exact questions have I asked you up until this message?",
                    },
                ]
            )
        finally:
            model.get_chat_model = get_chat_model
            model.get_valid_schools = get_valid_schools
            model.get_valid_major = get_valid_major
            model.get_valid_receiving_courses = get_valid_receiving_courses
            model.get_valid_cc_courses = get_valid_cc_courses
            model.search_articulations = search_articulations

        self.assertEqual(answer, "ok")
        self.assertIn("local_data_summary", calls["messages"][-1]["content"])
        self.assertNotIn("retrieved_articulation_rows", calls["messages"][-1]["content"])

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
