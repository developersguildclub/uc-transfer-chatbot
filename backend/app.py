from flask import Flask, redirect, render_template, request, session
from cs50 import SQL

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

