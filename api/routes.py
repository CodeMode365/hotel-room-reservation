import re
from datetime import date

import pymysql

from flask import Blueprint, jsonify, request

from database.db import get_db

api = Blueprint("api", __name__, url_prefix="/api")

ROOM_TYPES = ("standard", "deluxe", "suite")
MAX_PRICE = 1_000_000
MAX_NIGHTS = 365
ROOM_NUMBER_RE = re.compile(r"^[A-Za-z0-9-]{1,20}$")
PHONE_RE = re.compile(r"^\+?[\d ()-]{7,30}$")


# ---------- validation ----------
# Cleaners return (values, error). Never trust the client: the browser checks
# below are duplicated here because they are only a convenience there.

def _clean_room(data):
    number = str(data.get("room_number") or "").strip()
    if not ROOM_NUMBER_RE.match(number):
        return None, "room_number must be 1-20 letters, digits or dashes"

    room_type = str(data.get("room_type") or "standard").strip().lower()
    if room_type not in ROOM_TYPES:
        return None, f"room_type must be one of: {', '.join(ROOM_TYPES)}"

    try:
        price = round(float(data.get("price")), 2)
    except (TypeError, ValueError):
        return None, "price must be a number"
    if not 0 <= price <= MAX_PRICE:  # also rejects NaN and inf
        return None, f"price must be between 0 and {MAX_PRICE}"

    return {"room_number": number, "room_type": room_type, "price": price}, None


def _clean_reservation(data, is_new):
    try:
        room_id = int(data.get("room_id"))
    except (TypeError, ValueError):
        return None, "a room must be selected"

    name = str(data.get("guest_name") or "").strip()
    if not 2 <= len(name) <= 100 or not any(c.isalpha() for c in name):
        return None, "guest_name must be 2-100 characters and contain a letter"

    phone = str(data.get("guest_phone") or "").strip()
    if phone and not PHONE_RE.match(phone):
        return None, "guest_phone must be 7-30 digits, optionally starting with +"

    dates = {}
    for field in ("check_in", "check_out"):
        try:
            dates[field] = date.fromisoformat(str(data.get(field)))
        except ValueError:
            return None, f"{field} must be a valid YYYY-MM-DD date"

    nights = (dates["check_out"] - dates["check_in"]).days
    if nights < 1:
        return None, "check_out must be after check_in"
    if nights > MAX_NIGHTS:
        return None, f"a stay cannot exceed {MAX_NIGHTS} nights"
    # editing an in-progress stay is legitimate, so only new bookings are
    # required to start today or later
    if is_new and dates["check_in"] < date.today():
        return None, "check_in cannot be in the past"

    return {
        "room_id": room_id,
        "guest_name": name,
        "guest_phone": phone,
        "check_in": dates["check_in"].isoformat(),
        "check_out": dates["check_out"].isoformat(),
    }, None


def _check_availability(values, exclude_id=None):
    db = get_db()
    if not db.execute("SELECT 1 FROM rooms WHERE id = %s", (values["room_id"],)).fetchone():
        return "that room no longer exists"
    overlap = db.execute(
        """SELECT rooms.room_number FROM reservations
           JOIN rooms ON rooms.id = reservations.room_id
           WHERE room_id = %s AND NOT reservations.id <=> %s
             AND check_in < %s AND check_out > %s""",
        (values["room_id"], exclude_id, values["check_out"], values["check_in"]),
    ).fetchone()
    if overlap:
        return f"room {overlap['room_number']} is already booked for those dates"
    return None


# ---------- rooms ----------

@api.get("/rooms")
def list_rooms():
    rows = get_db().execute("SELECT * FROM rooms ORDER BY room_number").fetchall()
    return jsonify([dict(r) for r in rows])


@api.post("/rooms")
def create_room():
    values, error = _clean_room(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO rooms (room_number, room_type, price) VALUES (%s, %s, %s)",
            (values["room_number"], values["room_type"], values["price"]),
        )
        db.commit()
    except pymysql.err.IntegrityError:
        return jsonify({"error": f"room {values['room_number']} already exists"}), 409
    return jsonify({"id": cur.lastrowid}), 201


@api.put("/rooms/<int:room_id>")
def update_room(room_id):
    values, error = _clean_room(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), 400
    db = get_db()
    try:
        cur = db.execute(
            "UPDATE rooms SET room_number = %s, room_type = %s, price = %s WHERE id = %s",
            (values["room_number"], values["room_type"], values["price"], room_id),
        )
        db.commit()
    except pymysql.err.IntegrityError:
        return jsonify({"error": f"room {values['room_number']} already exists"}), 409
    if cur.rowcount == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


@api.delete("/rooms/<int:room_id>")
def delete_room(room_id):
    db = get_db()
    try:
        cur = db.execute("DELETE FROM rooms WHERE id = %s", (room_id,))
        db.commit()
    except pymysql.err.IntegrityError:
        return jsonify({"error": "this room has bookings, delete those first"}), 409
    if cur.rowcount == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


# ---------- reservations ----------

@api.get("/reservations")
def list_reservations():
    rows = get_db().execute(
        """SELECT res.*, rooms.room_number, rooms.price
           FROM reservations res JOIN rooms ON rooms.id = res.room_id
           ORDER BY res.check_in"""
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@api.post("/reservations")
def create_reservation():
    values, error = _clean_reservation(request.get_json(silent=True) or {}, is_new=True)
    if not error:
        error = _check_availability(values)
    if error:
        return jsonify({"error": error}), 400
    db = get_db()
    try:
        cur = db.execute(
            """INSERT INTO reservations (room_id, guest_name, guest_phone, check_in, check_out)
               VALUES (%s, %s, %s, %s, %s)""",
            (values["room_id"], values["guest_name"], values["guest_phone"],
             values["check_in"], values["check_out"]),
        )
        db.commit()
    except pymysql.err.IntegrityError:
        return jsonify({"error": "could not save that booking"}), 409
    return jsonify({"id": cur.lastrowid}), 201


@api.put("/reservations/<int:res_id>")
def update_reservation(res_id):
    values, error = _clean_reservation(request.get_json(silent=True) or {}, is_new=False)
    if not error:
        error = _check_availability(values, exclude_id=res_id)
    if error:
        return jsonify({"error": error}), 400
    db = get_db()
    try:
        cur = db.execute(
            """UPDATE reservations
               SET room_id = %s, guest_name = %s, guest_phone = %s, check_in = %s, check_out = %s
               WHERE id = %s""",
            (values["room_id"], values["guest_name"], values["guest_phone"],
             values["check_in"], values["check_out"], res_id),
        )
        db.commit()
    except pymysql.err.IntegrityError:
        return jsonify({"error": "could not save that booking"}), 409
    if cur.rowcount == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


@api.delete("/reservations/<int:res_id>")
def delete_reservation(res_id):
    db = get_db()
    cur = db.execute("DELETE FROM reservations WHERE id = %s", (res_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})
