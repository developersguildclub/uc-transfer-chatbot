from flask import Flask, request, jsonify
from flask_cors import CORS
from model import get_ai_response
from database import setup_database

app = Flask(__name__)
CORS(app)

# Create tables + insert starter data when backend starts
setup_database()

@app.route("/")
def index():
    return "Backend is running!"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")

    ai_reply = get_ai_response(user_message)

    return jsonify({
        "reply": ai_reply
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)