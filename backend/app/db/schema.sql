-- SQL schema for orders (initial)

CREATE TABLE IF NOT EXISTS "order" (
    id SERIAL PRIMARY KEY,
    raw_text TEXT NOT NULL,
    product_type VARCHAR(128),
    quantity INTEGER,
    size VARCHAR(64),
    paper_type VARCHAR(64),
    color VARCHAR(64),
    finishing TEXT,
    turnaround_days INTEGER,
    rush BOOLEAN DEFAULT FALSE,
    status VARCHAR(64),
    final_price NUMERIC,
    issues TEXT,
    email VARCHAR(256)
);
