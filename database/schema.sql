CREATE TABLE
    IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_number TEXT NOT NULL UNIQUE,
        room_type TEXT NOT NULL DEFAULT 'standard',
        price REAL NOT NULL CHECK (price >= 0)
    );

CREATE TABLE
    IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER NOT NULL REFERENCES rooms (id),
        guest_name TEXT NOT NULL,
        guest_phone TEXT NOT NULL DEFAULT '',
        check_in DATE NOT NULL,
        check_out DATE NOT NULL,
        CHECK (check_out > check_in)
    );