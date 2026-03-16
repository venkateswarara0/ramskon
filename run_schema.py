import psycopg2

DB_URL = "postgresql://ramskon_db_user:cgv6jhqMCY80PbDjRximtfYrB4HPAX7U@dpg-d6rvmptm5p6s73ah22cg-a.singapore-postgres.render.com/ramskon_db"

sql = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100),
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(10) DEFAULT 'user',
    is_approved BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    current_streak INT DEFAULT 0,
    best_streak INT DEFAULT 0,
    discipline_score INT DEFAULT 0,
    missed_days INT DEFAULT 0,
    last_completed_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS courses (
    id SERIAL PRIMARY KEY,
    course_name VARCHAR(100),
    description TEXT,
    category VARCHAR(50),
    duration_days INT DEFAULT 30,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_topics (
    id SERIAL PRIMARY KEY,
    course_id INT REFERENCES courses(id),
    day_number INT,
    topic_title VARCHAR(200),
    topic_description TEXT,
    assignment_title VARCHAR(200),
    assignment_description TEXT,
    local_resource_link TEXT,
    practice_task TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_requests (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    course_id INT REFERENCES courses(id),
    status VARCHAR(20) DEFAULT 'pending',
    is_completed BOOLEAN DEFAULT FALSE,
    badge_name VARCHAR(100),
    requested_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,
    completed_at TIMESTAMP,
    approved_by INT
);

CREATE TABLE IF NOT EXISTS user_progress (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    course_id INT REFERENCES courses(id),
    topic_id INT REFERENCES course_topics(id),
    day_number INT,
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    submission_text TEXT,
    submission_file VARCHAR(255),
    ai_score INT,
    ai_feedback TEXT,
    ai_evaluated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    title VARCHAR(200),
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
"""

try:
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(sql)
    cur.close()
    conn.close()
    print("✅ All tables created successfully!")
except Exception as e:
    print("❌ Error:", e)