"""
Flask server: serves web app, Chapa payments, services API, style uploads
"""

import os
import string
import random
import datetime

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import requests
import sqlite3

app = Flask(__name__)
CORS(app)

TOKEN = os.getenv("BOT_TOKEN", "")
CHAPA_SECRET = os.getenv("CHAPA_SECRET_KEY", "")
CHAPA_BASE = "https://api.chapa.co/v1"
WEB_APP_URL = os.getenv("WEB_APP_URL", "").rstrip("/")
CHAPA_WEBHOOK = os.getenv("CHAPA_WEBHOOK_URL", "")
WORKING_HOURS = ["09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00"]


def db():
    return sqlite3.connect("barber_shop.db", timeout=10)


def tx_ref(length=12):
    return "TX-" + "".join(random.choices(string.ascii_letters + string.digits, k=length))


# ────────────────────────────────────────────
# SERVE WEB APP
# ────────────────────────────────────────────
@app.route("/")
def index():
    return send_file("index.html")


# ────────────────────────────────────────────
# SERVE UPLOADED STYLE IMAGES
# ────────────────────────────────────────────
@app.route("/uploads/<path:filename>")
def uploaded(filename):
    return send_from_directory("uploads", filename)


# ────────────────────────────────────────────
# SERVICES API — web app fetches styles here
# ────────────────────────────────────────────
@app.route("/api/services")
def api_services():
    conn = db()
    rows = conn.cursor().execute(
        "SELECT id, name, price, description, est_time, image_path "
        "FROM services WHERE is_active=1 ORDER BY id"
    ).fetchall()
    conn.close()

    services = []
    for r in rows:
        img_url = f"{WEB_APP_URL}/uploads/{r[5]}" if r[5] else None
        services.append({
            "id": r[0], "name": r[1], "price": r[2],
            "description": r[3], "est_time": r[4], "image_url": img_url,
        })
    return jsonify({"services": services})


# ────────────────────────────────────────────
# AVAILABLE TIME SLOTS
# ────────────────────────────────────────────
@app.route("/api/get-times")
def get_times():
    date_str = request.args.get("date")
    conn = db()
    available = []
    for t in WORKING_HOURS:
        row = conn.cursor().execute(
            "SELECT 1 FROM appointments WHERE appointment_date=? AND appointment_time=? "
            "AND status IN ('booked','break') AND payment_status IN ('paid','pending')",
            (date_str, t)).fetchone()
        if not row:
            available.append(t)
    conn.close()
    return jsonify({"available_times": available})


# ────────────────────────────────────────────
# I18N STRINGS — web app fetches translations
# ────────────────────────────────────────────
@app.route("/api/i18n/<lang>")
def api_i18n(lang):
    """Return web-app-only strings for a given language.
    The bot already has translations built-in; this endpoint
    lets the web app stay in sync without duplicating the
    full dictionary in JS."""
    from barber import L
    web_keys = [k for k in L.get("en",{}) if k.startswith("w_")]
    result = {k: L.get(lang, L["en"]).get(k, L["en"].get(k, k)) for k in web_keys}
    return jsonify(result)


# ────────────────────────────────────────────
# CREATE CHAPA PAYMENT
# ────────────────────────────────────────────
@app.route("/api/create-payment", methods=["POST"])
def create_payment():
    data = request.json
    chat_id = data.get("chat_id")
    first_name = data.get("first_name", "Customer")
    service_name = data.get("service_name", "Unknown")
    service_price = data.get("service_price", 0)
    appt_date = data.get("date")
    appt_time = data.get("time")

    if not all([chat_id, appt_date, appt_time]):
        return jsonify({"error": "Missing booking data"}), 400

    ref = tx_ref()
    conn = db()

    # Check slot still free
    if conn.cursor().execute(
        "SELECT 1 FROM appointments WHERE appointment_date=? AND appointment_time=? "
        "AND status IN ('booked','break') AND payment_status != 'failed'",
        (appt_date, appt_time)).fetchone():
        conn.close()
        return jsonify({"error": "Slot just booked by someone else!"}), 400

    try:
        conn.cursor().execute(
            "INSERT INTO appointments (chat_id,client_name,phone,service,price,"
            "appointment_date,appointment_time,status,chapa_tx_ref,payment_status) "
            "VALUES (?,?,'Via WebApp',?,?,?,?,?,'booked',?,'pending')",
            (chat_id, first_name, f"{service_name}", service_price,
             appt_date, appt_time, ref))
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"error": "DB error", "details": str(e)}), 400
    finally:
        conn.close()

    # Call Chapa
    headers = {"Authorization": f"Bearer {CHAPA_SECRET}", "Content-Type": "application/json"}
    payload = {
        "amount": "50.00", "currency": "ETB",
        "email": f"tel_{chat_id}@booking.com",
        "first_name": first_name, "last_name": f"Client{chat_id}",
        "tx_ref": ref,
        "callback_url": CHAPA_WEBHOOK,
        "return_url": f"{WEB_APP_URL}?tx_ref={ref}",
    }
    resp = requests.post(f"{CHAPA_BASE}/transaction/initialize", json=payload, headers=headers)
    chapa = resp.json()

    if resp.status_code == 200 and "data" in chapa:
        return jsonify({"status": "success", "checkout_url": chapa["data"]["checkout_url"], "tx_ref": ref})

    # Mark failed
    conn = db()
    conn.cursor().execute("UPDATE appointments SET payment_status='failed',status='cancelled' WHERE chapa_tx_ref=?", (ref,))
    conn.commit(); conn.close()
    return jsonify({"error": "Chapa failed", "details": chapa}), 400


# ────────────────────────────────────────────
# CHAPA WEBHOOK
# ────────────────────────────────────────────
@app.route("/webhook/chapa", methods=["POST"])
def chapa_webhook():
    data = request.json
    ref = data.get("tx_ref")
    status = data.get("status")
    if status == "success":
        v = requests.get(f"{CHAPA_BASE}/transaction/verify/{ref}",
                         headers={"Authorization": f"Bearer {CHAPA_SECRET}"})
        if v.status_code == 200 and v.json().get("data",{}).get("status") == "success":
            conn = db()
            conn.cursor().execute("UPDATE appointments SET payment_status='paid' WHERE chapa_tx_ref=?", (ref,))
            conn.commit(); conn.close()
    return jsonify({"message": "ok"}), 200


# ────────────────────────────────────────────
# POLL PAYMENT STATUS
# ────────────────────────────────────────────
@app.route("/api/check-status")
def check_status():
    ref = request.args.get("tx_ref")
    if not ref: return jsonify({"error": "Missing tx_ref"}), 400
    conn = db()
    row = conn.cursor().execute("SELECT payment_status FROM appointments WHERE chapa_tx_ref=?", (ref,)).fetchone()
    conn.close()
    return jsonify({"payment_status": row[0] if row else "unknown"})


# ────────────────────────────────────────────
# FAKE PAYMENT (testing)
# ────────────────────────────────────────────
@app.route("/api/fake-payment", methods=["POST"])
def fake_payment():
    data = request.json
    ref = tx_ref()
    conn = db()
    conn.cursor().execute("INSERT INTO appointments (chat_id, client_name, phone, service, price, appointment_date, appointment_time, status, chapa_tx_ref, payment_status) VALUES (?, ?, 'N/A', ?, ?, ?, ?, 'booked', ?, 'paid')", (data.get("chat_id"), "Test User", data.get("service_name"), data.get("service_price", 0), data.get("date"), data.get("time"), ref))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "checkout_url": "fake", "tx_ref": ref})


# ────────────────────────────────────────────
# FALLBACK CONFIRM (if sendData fails)
# ────────────────────────────────────────────
@app.route("/api/confirm-booking", methods=["POST"])
def confirm_booking():
    data = request.json
    chat_id = data.get("chat_id")
    ref = data.get("tx_ref")
    image_url = data.get("image_url")
    style_name = data.get("style_name")
    style_desc = data.get("style_desc")

    conn = db()
    row = conn.cursor().execute(
        "SELECT payment_status FROM appointments WHERE chapa_tx_ref=?", (ref,)
    ).fetchone()

    if not row or row[0] != "paid":
        conn.close()
        print(f"[API] confirm-booking FAILED: not paid for {ref}")
        return jsonify({"error": "Not paid"}), 400

    conn.cursor().execute(
        "INSERT OR REPLACE INTO pending_web_data (chat_id,tx_ref,image_url,style_name,style_desc) VALUES (?,?,?,?,?)",
        (chat_id, ref, image_url, style_name, style_desc))
    conn.commit()
    conn.close()

    text = (
        "✅ *Payment confirmed!*\n\n"
        "Just one last thing — we need your phone number so the barber can reach you if needed.\n\n"
        "Tap the button below to share it securely (no typing needed):"
    )
    kb = {
        "keyboard": [[{"text": "📱 Share Phone Number", "request_contact": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "reply_markup": kb})
    print(f"[API] confirm-booking sent phone prompt to {chat_id}, status={resp.status_code}")

    return jsonify({"status": "success"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, use_reloader=False)