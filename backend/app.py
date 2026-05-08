from flask import Flask, redirect, render_template, request, session
from joblib import load
import numpy as np
from cs50 import SQL
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functions import login_required

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route("/home")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)