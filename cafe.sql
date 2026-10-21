-- =============================================
-- Cafe Website Database (SQLite)
-- =============================================

-- 1) Menu: what the customer sees
CREATE TABLE menu_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,          -- 'coffee', 'tea', 'dessert'
    price       REAL NOT NULL,          -- in BHD
    description TEXT
);

-- 2) Cafe tables: normal tables and study tables
CREATE TABLE cafe_tables (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    table_number INTEGER NOT NULL UNIQUE,
    type         TEXT NOT NULL CHECK (type IN ('normal', 'study')),
    seats        INTEGER NOT NULL,
    booking_fee  REAL NOT NULL DEFAULT 0  -- study tables have a fee
);

-- 3) Normal reservations
CREATE TABLE reservations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    phone         TEXT NOT NULL,          -- TEXT, not INTEGER (+973...)
    date          TEXT NOT NULL,          -- '2026-10-30'
    time          TEXT NOT NULL,          -- '19:30'
    people_count  INTEGER NOT NULL,
    notes         TEXT,
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'accepted', 'rejected')),
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 4) Study sessions (goal + penalty idea)
CREATE TABLE study_sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id         INTEGER NOT NULL REFERENCES cafe_tables(id),
    customer_name    TEXT NOT NULL,
    phone            TEXT NOT NULL,
    date             TEXT NOT NULL,
    start_time       TEXT NOT NULL,
    goal             TEXT NOT NULL,       -- 'Finish Wireless chapter 3'
    planned_hours    REAL NOT NULL,       -- customer's own estimate
    penalty_per_hour REAL NOT NULL DEFAULT 1.0,
    actual_hours     REAL,                -- filled when session ends
    goal_completed   INTEGER NOT NULL DEFAULT 0
                     CHECK (goal_completed IN (0, 1)),
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'accepted', 'rejected', 'finished')),
    created_at       TEXT DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- Sample data (for testing)
-- =============================================
INSERT INTO menu_items (name, category, price, description) VALUES
('Latte',          'coffee',  1.500, 'Espresso with steamed milk'),
('Spanish Latte',  'coffee',  1.800, 'Sweet latte with condensed milk'),
('Karak Tea',      'tea',     0.500, 'Spiced milk tea'),
('Cookie',         'dessert', 0.800, 'Chocolate chip cookie');

INSERT INTO cafe_tables (table_number, type, seats, booking_fee) VALUES
(1, 'normal', 4, 0),
(2, 'normal', 2, 0),
(3, 'study',  1, 2.000),
(4, 'study',  1, 2.000);

INSERT INTO reservations (customer_name, phone, date, time, people_count, notes) VALUES
('Ali', '+97333334444', '2026-10-30', '19:30', 3, 'Outdoor table please');

INSERT INTO study_sessions (table_id, customer_name, phone, date, start_time, goal, planned_hours) VALUES
(3, 'Salman', '+97333335555', '2026-10-30', '16:00', 'Finish Wireless chapter 3', 3);
