from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_bcrypt import Bcrypt
import sqlite3
import os
import pyotp
import qrcode
from io import BytesIO
import base64

from crawler import crawl
from preprocess import preprocess
from indexer import build_index
from ranker import compute_tfidf
from search import search
from utils import save_data, load_data

app = Flask(__name__)
app.secret_key = "supersecretkey"  # 🔐 Change later
bcrypt = Bcrypt(app)

# ---------------- DATABASE ---------------- #
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            secret TEXT
        )
    """)

    # 🔥 NEW: History table
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            query TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- SEARCH ENGINE LOAD ---------------- #
seed_urls = [
    "https://en.wikipedia.org/wiki/Search_engine",
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://en.wikipedia.org/wiki/Computer_network",
    "https://en.wikipedia.org/wiki/Data_structure",
    "https://en.wikipedia.org/wiki/Machine_learning"
]

DATA_FILE = "engine_data.pkl"

if os.path.exists(DATA_FILE):
    data = load_data(DATA_FILE)
    documents = data["documents"]
    processed_docs = data["processed_docs"]
    index = data["index"]
    tfidf = data["tfidf"]
    vocab = set()
    for doc in processed_docs.values():
        vocab.update(doc)
else:
    documents = crawl(seed_urls, max_pages=30)
    processed_docs = preprocess(documents)
    vocab = set()
    for doc in processed_docs.values():
        vocab.update(doc)
    index = build_index(processed_docs)
    tfidf = compute_tfidf(processed_docs)

    save_data(DATA_FILE, {
        "documents": documents,
        "processed_docs": processed_docs,
        "index": index,
        "tfidf": tfidf
    })

# ---------------- AUTH ROUTES ---------------- #

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        secret = pyotp.random_base32()
        try:
            conn = sqlite3.connect("users.db")
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password, secret) VALUES (?, ?, ?)", (username, hashed_pw, secret))
            conn.commit()
            conn.close()

            flash("Registration successful! Please login.")
            return redirect(f"/setup-2fa/{username}")

        except:
            flash("Username already exists!")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user[2], password):
            session["temp_user"] = username   # 🔥 NOT logged in yet
            return redirect("/verify-otp")
        else:
            flash("Invalid credentials!")

        if user and bcrypt.check_password_hash(user[2], password):
            session["temp_user"] = username   # not fully logged in yet
            return redirect("/verify-otp")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")


@app.route("/setup-2fa/<username>")
def setup_2fa(username):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT secret FROM users WHERE username=?", (username,))
    secret = c.fetchone()[0]
    conn.close()

    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name="MiniSearchEngine"
    )

    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    img_base64 = base64.b64encode(buf.getvalue()).decode()

    return render_template("setup_2fa.html", qr=img_base64)


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if "temp_user" not in session:
        return redirect("/login")

    if request.method == "POST":
        otp = request.form["otp"]

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT secret FROM users WHERE username=?", (session["temp_user"],))
        secret = c.fetchone()[0]
        conn.close()

        totp = pyotp.TOTP(secret)

        if totp.verify(otp):
            session["user"] = session.pop("temp_user")
            return redirect("/")
        else:
            flash("Invalid OTP")

    return render_template("verify_otp.html")


# ---------------- MAIN ROUTES ---------------- #

@app.route("/")
def home():
    user = session.get("user")
    history = []

    if user:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("""
            SELECT query FROM history 
            WHERE username=? 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (user,))
        row = c.fetchone()
        history = row[0] if row else None
        conn.close()

    return render_template("index.html", user=user, history=history)

@app.route("/search")
def search_page():
    query = request.args.get("query")   # ✅ ALWAYS FIRST
    results = []
    user = session.get("user")          # ✅ SAFE

    if query:

        # ✅ Save history ONLY if logged in
        if user:
            conn = sqlite3.connect("users.db")
            c = conn.cursor()
            c.execute("INSERT INTO history (username, query) VALUES (?, ?)",
                      (user, query))
            conn.commit()
            conn.close()

        # 🔍 Search logic
        ranked, corrected_query = search(query, index, tfidf, processed_docs, vocab)
        suggestion = None
        if corrected_query != query.lower():
            suggestion = corrected_query

        for url, score in ranked:
            data = documents[url]
            full_text = data["text"]

            import re
            paragraphs = re.split(r'\n+', full_text)
            paragraph = next((p for p in paragraphs if len(p) > 100), full_text[:300])

            results.append({
                "title": data["title"],
                "url": url,
                "snippet": full_text[:200],
                "preview": paragraph,
                "score": round(score, 4)
            })

    return render_template(
        "results.html",
        query=query,
        results=results,
        suggestion=suggestion
    )
@app.route("/history")
def view_history():
    user = session.get("user")

    if not user:
        return redirect("/login")

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("""
        SELECT query, timestamp 
        FROM history 
        WHERE username=? 
        ORDER BY timestamp DESC
    """, (user,))

    history = c.fetchall()
    conn.close()

    return render_template("history.html", history=history, user=user)

@app.route("/latest-search")
def latest_search():
    user = session.get("user")

    if not user:
        return {"query": None}

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        SELECT query FROM history 
        WHERE username=? 
        ORDER BY timestamp DESC 
        LIMIT 1
    """, (user,))
    
    row = c.fetchone()
    conn.close()

    return {"query": row[0] if row else None}


@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    response.cache_control.no_cache = True
    response.cache_control.must_revalidate = True
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == "__main__":
    app.run(debug=True)