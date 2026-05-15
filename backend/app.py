from flask import Flask, redirect, jsonify, request, session
from flask_cors import CORS


app = Flask(__name__)

# allow frontend to call backend during development
CORS(app)

# making sure backend is running
@app.route("/")
def index():
    return "Backend is running!"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    user_message = data.get("message", "")

    return jsonify({
        "reply": f"You said: {user_message}"
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)