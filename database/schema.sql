CREATE TABLE
    IF NOT EXISTS rooms (
        id INT AUTO_INCREMENT PRIMARY KEY,
        room_number VARCHAR(20) NOT NULL UNIQUE,
        room_type VARCHAR(50) NOT NULL DEFAULT 'standard',
        price DECIMAL(10, 2) NOT NULL CHECK (price >= 0)
    );

CREATE TABLE
    IF NOT EXISTS reservations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        room_id INT NOT NULL,
        guest_name VARCHAR(100) NOT NULL,
        guest_phone VARCHAR(30) NOT NULL DEFAULT '',
        check_in DATE NOT NULL,
        check_out DATE NOT NULL,
        FOREIGN KEY (room_id) REFERENCES rooms (id),
        CHECK (check_out > check_in)
    );
