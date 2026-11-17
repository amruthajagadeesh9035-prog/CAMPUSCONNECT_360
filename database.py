
import sqlite3

DATABASE = "campusconnect.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():

    conn = get_db_connection()

    # Students Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            registered_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Check Student Table Columns
    student_columns = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(students)"
        ).fetchall()
    ]

    if "registered_at" not in student_columns:
        conn.execute(
            "ALTER TABLE students ADD COLUMN registered_at TEXT"
        )

    # Update Existing Student Registration Dates
    conn.execute("""
        UPDATE students
        SET registered_at = CURRENT_TIMESTAMP
        WHERE registered_at IS NULL
    """)

    # Events Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            event_date TEXT NOT NULL,
            location TEXT
        )
    """)

    # Attendance Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            event_id INTEGER,
            status TEXT DEFAULT 'Present'
        )
    """)

    # Admins Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Event Registration Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS event_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, event_id),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)

    # Announcements Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Student Feedback Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            event_id INTEGER,
            feedback_text TEXT NOT NULL,
            rating INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)

    # Notifications Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add Student ID to Existing Notifications Table
    notification_columns = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(notifications)"
        ).fetchall()
    ]

    if "student_id" not in notification_columns:
        conn.execute(
            "ALTER TABLE notifications ADD COLUMN student_id INTEGER"
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    print("CAMPUSCONNECT 360 database is ready!")
