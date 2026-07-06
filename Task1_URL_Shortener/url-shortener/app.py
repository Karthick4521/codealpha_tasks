from flask import Flask, request, redirect, render_template, jsonify, url_for
import sqlite3
import string
import random
import os

app = Flask(__name__)
DB_NAME = "database.db"


# ---------------------------
# Database setup
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------
# Helper: generate unique short code
# ---------------------------
def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choices(characters, k=length))
        conn = get_db_connection()
        existing = conn.execute(
            "SELECT 1 FROM urls WHERE short_code = ?", (code,)
        ).fetchone()
        conn.close()
        if not existing:
            return code


# ---------------------------
# Frontend route
# ---------------------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------------------
# API: Shorten a URL
# ---------------------------
@app.route("/api/shorten", methods=["POST"])
def shorten_url():
    data = request.get_json(silent=True) or request.form
    original_url = data.get("url", "").strip()

    if not original_url:
        return jsonify({"error": "URL is required"}), 400

    if not (original_url.startswith("http://") or original_url.startswith("https://")):
        original_url = "https://" + original_url

    conn = get_db_connection()
    existing = conn.execute(
        "SELECT short_code FROM urls WHERE original_url = ?", (original_url,)
    ).fetchone()

    if existing:
        short_code = existing["short_code"]
    else:
        short_code = generate_short_code()
        conn.execute(
            "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
            (short_code, original_url),
        )
        conn.commit()

    conn.close()

    short_url = request.host_url + short_code
    return jsonify({
        "original_url": original_url,
        "short_code": short_code,
        "short_url": short_url
    }), 201


# ---------------------------
# API: List all URLs (optional, useful for testing)
# ---------------------------
@app.route("/api/urls", methods=["GET"])
def list_urls():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT short_code, original_url, created_at FROM urls ORDER BY id DESC"
    ).fetchall()
    conn.close()

    urls = [dict(row) for row in rows]
    return jsonify(urls), 200


# ---------------------------
# Redirect route
# ---------------------------
@app.route("/<short_code>")
def redirect_to_url(short_code):
    conn = get_db_connection()
    result = conn.execute(
        "SELECT original_url FROM urls WHERE short_code = ?", (short_code,)
    ).fetchone()
    conn.close()

    if result:
        return redirect(result["original_url"])
    else:
        return render_template("404.html"), 404


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
