"""Self-check for the request validators. Run: python test_validation.py"""

from datetime import date, timedelta

from api.routes import _clean_reservation, _clean_room

TODAY = date.today()
SOON = (TODAY + timedelta(days=1)).isoformat()
LATER = (TODAY + timedelta(days=3)).isoformat()


def ok(values, error):
    assert error is None, error
    return values


def rejected(values, error):
    assert values is None and error, "expected a rejection"


def test_rooms():
    room = ok(*_clean_room({"room_number": " a-12 ", "room_type": "SUITE", "price": "99.999"}))
    assert room == {"room_number": "a-12", "room_type": "suite", "price": 100.0}

    # room_type defaults, but an unknown one is not silently accepted
    assert ok(*_clean_room({"room_number": "1", "price": 0}))["room_type"] == "standard"
    rejected(*_clean_room({"room_number": "1", "room_type": "penthouse", "price": 1}))

    rejected(*_clean_room({"room_number": "", "price": 1}))
    rejected(*_clean_room({"room_number": "room 1!", "price": 1}))  # bad characters
    rejected(*_clean_room({"room_number": "x" * 21, "price": 1}))
    rejected(*_clean_room({"room_number": "1", "price": None}))
    rejected(*_clean_room({"room_number": "1", "price": "free"}))
    rejected(*_clean_room({"room_number": "1", "price": -1}))
    rejected(*_clean_room({"room_number": "1", "price": 1e9}))
    rejected(*_clean_room({"room_number": "1", "price": float("nan")}))
    rejected(*_clean_room({"room_number": "1", "price": float("inf")}))


def booking(**overrides):
    return {"room_id": 1, "guest_name": "Jane Doe", "check_in": SOON,
            "check_out": LATER, **overrides}


def test_reservations():
    values = ok(*_clean_reservation(booking(guest_phone=" +977 980-000 "), is_new=True))
    assert values["guest_phone"] == "+977 980-000"
    assert values["check_in"] == SOON and values["check_out"] == LATER

    rejected(*_clean_reservation(booking(room_id=""), is_new=True))
    rejected(*_clean_reservation(booking(guest_name=" J "), is_new=True))
    rejected(*_clean_reservation(booking(guest_name="12345"), is_new=True))
    rejected(*_clean_reservation(booking(guest_phone="pick up the phone"), is_new=True))
    rejected(*_clean_reservation(booking(check_in="tomorrow"), is_new=True))
    rejected(*_clean_reservation(booking(check_in="2026-13-40"), is_new=True))
    rejected(*_clean_reservation(booking(check_out=SOON), is_new=True))  # zero nights
    rejected(*_clean_reservation(booking(check_in=LATER, check_out=SOON), is_new=True))
    rejected(*_clean_reservation(
        booking(check_out=(TODAY + timedelta(days=400)).isoformat()), is_new=True))

    # past check-in: blocked for new bookings, allowed when editing a live stay
    past = booking(check_in=(TODAY - timedelta(days=2)).isoformat())
    rejected(*_clean_reservation(past, is_new=True))
    ok(*_clean_reservation(past, is_new=False))


if __name__ == "__main__":
    test_rooms()
    test_reservations()
    print("validation ok")
