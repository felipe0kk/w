from __future__ import annotations
import os, sys, json, sqlite3, threading, time, webbrowser
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, render_template, request

APP_NAME = "Steam Key Hunter"
VERSION = "2.0.0"
API_URL = "https://www.gamerpower.com/api/giveaways"
REFRESH_SECONDS = max(300, int(os.getenv("REFRESH_SECONDS", "900")))
PORT = int(os.getenv("PORT", "5187"))
REQUEST_TIMEOUT = 20

def resource_path(relative):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / relative

def data_directory():
    if os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA", Path.home())) / "SteamKeyHunter"
    else:
        root = Path.home() / ".steam-key-hunter"
    root.mkdir(parents=True, exist_ok=True)
    return root

DB_PATH = data_directory() / "steam_key_hunter_v2.db"
app = Flask(__name__, template_folder=str(resource_path("templates")),
            static_folder=str(resource_path("static")))
app.config["JSON_SORT_KEYS"] = False
refresh_lock = threading.Lock()
state_lock = threading.Lock()
state = {"ok": False, "message": "Preparado para buscar.", "at": None, "busy": False}

KEY_TERMS = (
    "steam key", "steam keys", "key giveaway", "keys giveaway", "cd key",
    "cd-key", "game key", "game keys", "redeem code", "activation code",
    "steam code", "key drop", "free key", "free keys", "product key"
)

def db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS offers (
          id INTEGER PRIMARY KEY, title TEXT NOT NULL, worth TEXT, thumbnail TEXT,
          description TEXT, instructions TEXT, giveaway_url TEXT, source_url TEXT,
          published_date TEXT, end_date TEXT, platforms TEXT, giveaway_type TEXT,
          users INTEGER DEFAULT 0, status TEXT, is_key INTEGER DEFAULT 0,
          first_seen TEXT NOT NULL, last_seen TEXT NOT NULL
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
          offer_id INTEGER PRIMARY KEY, added_at TEXT NOT NULL
        )""")
        conn.commit()

def safe_url(value):
    try:
        p = urlparse(str(value or ""))
        return str(value) if p.scheme in ("http", "https") and p.netloc else None
    except ValueError:
        return None

def classify(item):
    text = " ".join(str(item.get(k, "")) for k in
                    ("title", "description", "instructions", "type")).lower()
    # Heurística transparente: indica un posible reparto de clave, no lo garantiza.
    return any(term in text for term in KEY_TERMS)

def normalize(item):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
      "id": int(item["id"]), "title": str(item.get("title") or "Promoción")[:300],
      "worth": str(item.get("worth") or "No especificado")[:60],
      "thumbnail": safe_url(item.get("thumbnail")),
      "description": str(item.get("description") or "")[:6000],
      "instructions": str(item.get("instructions") or "")[:6000],
      "giveaway_url": safe_url(item.get("open_giveaway_url")),
      "source_url": safe_url(item.get("gamerpower_url")),
      "published_date": str(item.get("published_date") or ""),
      "end_date": str(item.get("end_date") or ""),
      "platforms": str(item.get("platforms") or "Steam"),
      "giveaway_type": str(item.get("type") or "Game"),
      "users": int(item.get("users") or 0),
      "status": str(item.get("status") or "Active"),
      "is_key": int(classify(item)),
      "first_seen": now, "last_seen": now
    }

def refresh():
    if not refresh_lock.acquire(blocking=False):
        return False, "Ya hay una búsqueda en curso."
    with state_lock:
        state["busy"] = True
    try:
        try:
            response = requests.get(
                API_URL,
                params={"platform": "steam", "type": "game", "sort-by": "date"},
                headers={"User-Agent": "SteamKeyHunter/2.0 (+local giveaway tracker)"},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                payload = payload.get("giveaways", [])
            if not isinstance(payload, list):
                raise ValueError("La fuente devolvió un formato inesperado.")

            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            count = 0
            with db() as conn:
                for raw in payload:
                    if not isinstance(raw, dict) or not raw.get("id"):
                        continue
                    item = normalize(raw)
                    conn.execute("""
                        INSERT INTO offers (id,title,worth,thumbnail,description,instructions,
                          giveaway_url,source_url,published_date,end_date,platforms,giveaway_type,
                          users,status,is_key,first_seen,last_seen)
                        VALUES (:id,:title,:worth,:thumbnail,:description,:instructions,
                          :giveaway_url,:source_url,:published_date,:end_date,:platforms,:giveaway_type,
                          :users,:status,:is_key,:first_seen,:last_seen)
                        ON CONFLICT(id) DO UPDATE SET title=excluded.title,worth=excluded.worth,
                          thumbnail=excluded.thumbnail,description=excluded.description,
                          instructions=excluded.instructions,giveaway_url=excluded.giveaway_url,
                          source_url=excluded.source_url,published_date=excluded.published_date,
                          end_date=excluded.end_date,platforms=excluded.platforms,
                          giveaway_type=excluded.giveaway_type,users=excluded.users,
                          status=excluded.status,is_key=excluded.is_key,last_seen=excluded.last_seen
                    """, item)
                    count += 1
                conn.commit()
            msg = f"Consulta completada: {count} promociones recibidas."
            with state_lock:
                state.update(ok=True, message=msg, at=now)
            return True, msg
        except requests.RequestException as exc:
            msg = f"No se pudo conectar con GamerPower: {exc}"
        except (ValueError, json.JSONDecodeError) as exc:
            msg = f"Respuesta no válida de la fuente: {exc}"
        except Exception as exc:
            msg = f"Error inesperado: {exc}"
        with state_lock:
            state.update(ok=False, message=msg,
                         at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        return False, msg
    finally:
        with state_lock:
            state["busy"] = False
        refresh_lock.release()

def background_worker():
    while True:
        time.sleep(REFRESH_SECONDS)
        refresh()

def offer_rows(mode="all", query=""):
    query = query.strip().lower()
    with db() as conn:
        rows = conn.execute("""
          SELECT o.*, CASE WHEN f.offer_id IS NULL THEN 0 ELSE 1 END AS favorite
          FROM offers o LEFT JOIN favorites f ON f.offer_id=o.id
          ORDER BY o.last_seen DESC
        """).fetchall()
    out = []
    for r in rows:
        x = dict(r)
        if mode == "keys" and not x["is_key"]: continue
        if mode == "favorites" and not x["favorite"]: continue
        if query and query not in (x["title"] + " " + x["description"]).lower(): continue
        out.append(x)
    return out

@app.get("/")
def home():
    return render_template("index.html", version=VERSION)

@app.get("/api/offers")
def offers():
    mode = request.args.get("mode", "all")
    if mode not in ("all", "keys", "favorites"): mode = "all"
    q = request.args.get("q", "")[:120]
    rows = offer_rows(mode, q)
    return jsonify({"offers": rows, "state": dict(state), "refresh_seconds": REFRESH_SECONDS,
                    "source": "GamerPower", "version": VERSION})

@app.post("/api/refresh")
def api_refresh():
    ok, message = refresh()
    return jsonify({"ok": ok, "message": message, "state": dict(state)}), (200 if ok else 502)

@app.post("/api/favorites/<int:offer_id>")
def toggle_favorite(offer_id):
    with db() as conn:
        exists = conn.execute("SELECT 1 FROM favorites WHERE offer_id=?", (offer_id,)).fetchone()
        if exists:
            conn.execute("DELETE FROM favorites WHERE offer_id=?", (offer_id,))
            favorite = False
        else:
            conn.execute("INSERT OR IGNORE INTO favorites VALUES (?,?)",
                         (offer_id, datetime.now(timezone.utc).isoformat(timespec="seconds")))
            favorite = True
        conn.commit()
    return jsonify({"ok": True, "favorite": favorite})

@app.get("/api/status")
def status():
    return jsonify({"status": "ok", "version": VERSION, "state": dict(state)})

def launch():
    init_db()
    threading.Thread(target=background_worker, daemon=True).start()
    # Espera a que Flask esté disponible y abre el navegador del usuario.
    threading.Thread(target=lambda: (time.sleep(1.4), webbrowser.open(f"http://127.0.0.1:{PORT}")),
                     daemon=True).start()
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False, threaded=True)

if __name__ == "__main__":
    launch()
