CREATE TABLE generation_requests (
    id UUID PRIMARY KEY,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_text TEXT NOT NULL,
    generated_text TEXT,
    status VARCHAR(20) DEFAULT 'in_progress'
);
