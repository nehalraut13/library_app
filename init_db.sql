CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    name TEXT,
    seat_no TEXT,
    mobile_no TEXT,
    fee_paid TEXT,
    plan_type TEXT,
    start_date TEXT,
    end_date TEXT,
    aadhaar_photo TEXT
);
