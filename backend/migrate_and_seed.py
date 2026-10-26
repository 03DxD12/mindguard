"""
MindGuard Database Migration and Seed Script
Ensures schema completeness and seeds admin & staff credentials for both SQLite and MySQL.
"""
import os
import sys
import sqlite3
import bcrypt

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(SCRIPT_DIR, "mindguard.db")

def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_pw(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def migrate_and_seed_sqlite():
    print("\n--- Migrating & Seeding SQLite ---")
    conn = sqlite3.connect(SQLITE_PATH)
    cur = conn.cursor()

    # Step 1: Check columns in users table
    cur.execute("PRAGMA table_info(users)")
    cols = [r[1] for r in cur.fetchall()]
    print("SQLite users columns before:", cols)

    if "is_primary_admin" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN is_primary_admin BOOLEAN NOT NULL DEFAULT 0")
        print("✅ Added is_primary_admin to SQLite users")
    if "trusted_contacts" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN trusted_contacts TEXT NULL")
        print("✅ Added trusted_contacts to SQLite users")

    conn.commit()

    # Step 2: Seed / Update Admins
    admin_hash = hash_pw("adminpiyu123")
    staff_hash = hash_pw("kapeeryu123")

    # Primary Admin
    cur.execute("SELECT id FROM users WHERE email = ?", ("adminkapeeryu@edu.ph",))
    row = cur.fetchone()
    if row:
        cur.execute("""
            UPDATE users SET password_hash = ?, role = 'admin', is_primary_admin = 1, fullname = 'MindGuard Administrator'
            WHERE email = ?
        """, (admin_hash, "adminkapeeryu@edu.ph"))
        print("✅ Updated adminkapeeryu@edu.ph in SQLite")
    else:
        cur.execute("""
            INSERT INTO users (email, password_hash, role, fullname, is_primary_admin)
            VALUES (?, ?, 'admin', 'MindGuard Administrator', 1)
        """, ("adminkapeeryu@edu.ph", admin_hash))
        print("✅ Inserted adminkapeeryu@edu.ph in SQLite")

    # Staff
    cur.execute("SELECT id FROM users WHERE email = ?", ("kapeeryu@mindguard.edu.ph",))
    row = cur.fetchone()
    if row:
        cur.execute("""
            UPDATE users SET password_hash = ?, role = 'staff', is_primary_admin = 0, fullname = 'Ka-PEER Yu Staff', program = 'Ka-PEER Yu'
            WHERE email = ?
        """, (staff_hash, "kapeeryu@mindguard.edu.ph"))
        print("✅ Updated kapeeryu@mindguard.edu.ph in SQLite")
    else:
        cur.execute("""
            INSERT INTO users (email, password_hash, role, fullname, is_primary_admin, program)
            VALUES (?, ?, 'staff', 'Ka-PEER Yu Staff', 0, 'Ka-PEER Yu')
        """, ("kapeeryu@mindguard.edu.ph", staff_hash))
        print("✅ Inserted kapeeryu@mindguard.edu.ph in SQLite")

    conn.commit()

    # Verify
    cur.execute("SELECT id, email, role, is_primary_admin, password_hash FROM users")
    users = cur.fetchall()
    print(f"SQLite users total: {len(users)}")
    for u in users:
        test_pw = "adminpiyu123" if "admin" in u[1] else "kapeeryu123"
        valid = verify_pw(test_pw, u[4])
        print(f"  {u[1]} | role={u[2]} | primary={u[3]} | pw_verify={'✅ PASS' if valid else '❌ FAIL'}")

    conn.close()

def migrate_and_seed_mysql():
    print("\n--- Migrating & Seeding MySQL (MariaDB) ---")
    try:
        import pymysql
        conn = pymysql.connect(
            host="localhost",
            port=3307,
            user="root",
            password="1213",
            database="mindguard",
            charset="utf8mb4"
        )
        cur = conn.cursor()

        # Check columns
        cur.execute("DESCRIBE users")
        cols = [r[0] for r in cur.fetchall()]
        if "is_primary_admin" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN is_primary_admin TINYINT(1) NOT NULL DEFAULT 0")
            print("✅ Added is_primary_admin to MySQL users")
        if "trusted_contacts" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN trusted_contacts VARCHAR(255) NULL")
            print("✅ Added trusted_contacts to MySQL users")
        conn.commit()

        # Create any missing tables using models
        from sqlalchemy import create_engine
        import models
        mysql_engine = create_engine("mysql+pymysql://root:1213@localhost:3307/mindguard")
        models.Base.metadata.create_all(bind=mysql_engine)
        print("✅ MySQL models.Base.metadata.create_all verified")

        admin_hash = hash_pw("adminpiyu123")
        staff_hash = hash_pw("kapeeryu123")

        # Primary Admin
        cur.execute("SELECT id FROM users WHERE email = %s", ("adminkapeeryu@edu.ph",))
        if cur.fetchone():
            cur.execute("""
                UPDATE users SET password_hash = %s, role = 'admin', is_primary_admin = 1, fullname = 'MindGuard Administrator'
                WHERE email = %s
            """, (admin_hash, "adminkapeeryu@edu.ph"))
        else:
            cur.execute("""
                INSERT INTO users (email, password_hash, role, fullname, is_primary_admin)
                VALUES (%s, %s, 'admin', 'MindGuard Administrator', 1)
            """, ("adminkapeeryu@edu.ph", admin_hash))

        # Staff
        cur.execute("SELECT id FROM users WHERE email = %s", ("kapeeryu@mindguard.edu.ph",))
        if cur.fetchone():
            cur.execute("""
                UPDATE users SET password_hash = %s, role = 'staff', is_primary_admin = 0, fullname = 'Ka-PEER Yu Staff', program = 'Ka-PEER Yu'
                WHERE email = %s
            """, (staff_hash, "kapeeryu@mindguard.edu.ph"))
        else:
            cur.execute("""
                INSERT INTO users (email, password_hash, role, fullname, is_primary_admin, program)
                VALUES (%s, %s, 'staff', 'Ka-PEER Yu Staff', 0, 'Ka-PEER Yu')
            """, ("kapeeryu@mindguard.edu.ph", staff_hash))

        conn.commit()

        # Verify
        cur.execute("SELECT id, email, role, is_primary_admin, password_hash FROM users")
        for u in cur.fetchall():
            test_pw = "adminpiyu123" if "admin" in u[1] else "kapeeryu123"
            valid = verify_pw(test_pw, u[4])
            print(f"  {u[1]} | role={u[2]} | primary={u[3]} | pw_verify={'✅ PASS' if valid else '❌ FAIL'}")

        conn.close()
    except Exception as e:
        print(f"⚠️  MySQL migration skipped/failed: {e}")

if __name__ == "__main__":
    migrate_and_seed_sqlite()
    migrate_and_seed_mysql()
    print("\n✅ Migration and Seeding Complete!")
