import psycopg2
from werkzeug.security import generate_password_hash

DB_URL = "postgresql://ramskon_db_user:cgv6jhqMCY80PbDjRximtfYrB4HPAX7U@dpg-d6rvmptm5p6s73ah22cg-a.singapore-postgres.render.com/ramskon_db"

try:
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users (full_name, email, password_hash, role, is_approved)
        VALUES (%s, %s, %s, 'admin', TRUE)
        ON CONFLICT (email) DO NOTHING
    """, (
        "Admin",
        "admin@ramskon.com",
        generate_password_hash("admin123")
    ))

    cur.close()
    conn.close()
    print("✅ Admin created! Email: admin@ramskon.com | Password: admin123")
except Exception as e:
    print("❌ Error:", e)