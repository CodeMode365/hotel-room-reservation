import sqlite3

from flask import Blueprint, jsonify, request

from database.db import get_db

api = Blueprint("api", __name__, url_prefix="/api")


# ---------- rooms ----------

@api.get("/rooms")
def list_rooms():
    rows = get_db().execute("SELECT * FROM rooms ORDER BY room_number").fetchall()
    return jsonify([dict(r) for r in rows])


@api.post("/rooms")
def create_room():
    data = request.get_json(silent=True) or {}
    if not data.get("room_number") or data.get("price") is None:
        return jsonify({"error": "room_number and price are required"}), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO rooms (room_number, room_type, price) VALUES (?, ?, ?)",
            (data["room_number"], data.get("room_type", "standard"), data["price"]),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        return jsonify({"error": str(e)}), 409
    return jsonify({"id": cur.lastrowid}), 201


@api.put("/rooms/<int:room_id>")
def update_room(room_id):
    data = request.get_json(silent=True) or {}
    if not data.get("room_number") or data.get("price") is None:
        return jsonify({"error": "room_number and price are required"}), 400
    db = get_db()
    try:
        cur = db.execute(
            "UPDATE rooms SET room_number = ?, room_type = ?, price = ? WHERE id = ?",
            (data["room_number"], data.get("room_type", "standard"), data["price"], room_id),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        return jsonify({"error": str(e)}), 409
    if cur.rowcount == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


@api.delete("/rooms/<int:room_id>")
def delete_room(room_id):
    db = get_db()
    try:
        cur = db.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "room has reservations"}), 409
    if cur.rowcount == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


# ---------- reservations ----------

@api.get("/reservations")
def list_reservations():
    rows = get_db().execute(
        """SELECT res.*, rooms.room_number
           FROM reservations res JOIN rooms ON rooms.id = res.room_id
           ORDER BY res.check_in"""
    ).fetchall()
    return jsonify([dict(r) for r in rows])


def _validate_reservation(data, exclude_id=None):
    required = ("room_id", "guest_name", "check_in", "check_out")
    if any(not data.get(k) for k in required):
        return "room_id, guest_name, check_in and check_out are required"
    if data["check_out"] <= data["check_in"]:
        return "check_out must be after check_in"
    overlap = get_db().execute(
        """SELECT 1 FROM reservations
           WHERE room_id = ? AND id IS NOT ? AND check_in < ? AND check_out > ?""",
        (data["room_id"], exclude_id, data["check_out"], data["check_in"]),
    ).fetchone()
    if overlap:
        return "room already booked for those dates"
    return None


@api.post("/reservations")
def create_reservation():
    data = request.get_json(silent=True) or {}
    error = _validate_reservation(data)
    if error:
        return jsonify({"error": error}), 400
    db = get_db()
    try:
        cur = db.execute(
            """INSERT INTO reservations (room_id, guest_name, guest_phone, check_in, check_out)
               VALUES (?, ?, ?, ?, ?)""",
            (data["room_id"], data["guest_name"], data.get("guest_phone", ""),
             data["check_in"], data["check_out"]),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        return jsonify({"error": str(e)}), 409
    return jsonify({"id": cur.lastrowid}), 201


@api.put("/reservations/<int:res_id>")
def update_reservation(res_id):
    data = request.get_json(silent=True) or {}
    error = _validate_reservation(data, exclude_id=res_id)
    if error:
        return jsonify({"error": error}), 400
    db = get_db()
    try:
        cur = db.execute(
            """UPDATE reservations
               SET room_id = ?, guest_name = ?, guest_phone = ?, check_in = ?, check_out = ?
               WHERE id = ?""",
            (data["room_id"], data["guest_name"], data.get("guest_phone", ""),
             data["check_in"], data["check_out"], res_id),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        return jsonify({"error": str(e)}), 409
    if cur.rowcount == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


@api.delete("/reservations/<int:res_id>")
def delete_reservation(res_id):
    db = get_db()
    cur = db.execute("DELETE FROM reservations WHERE id = ?", (res_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})
