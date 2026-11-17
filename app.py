
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import create_tables, get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "campusconnect_secret_key_2026"

create_tables()


# Admin Access Protection
def admin_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):

        if "admin_id" not in session:
            flash("Please login as admin first.")
            return redirect(url_for("admin_login"))

        return route_function(*args, **kwargs)

    return wrapper


# Home Page
@app.route("/")
def home():
    return render_template("index.html")


# Student Registration
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()

        try:
            conn.execute(
                """INSERT INTO students
                   (name, email, password, registered_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                (name, email, hashed_password)
            )

            conn.commit()

            flash("Registration successful! Please login.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("This email is already registered.")

        finally:
            conn.close()

    return render_template("register.html")


# Student Login
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()

        student = conn.execute(
            "SELECT * FROM students WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        if student and check_password_hash(
            student["password"], password
        ):

            session.clear()
            session["student_id"] = student["id"]
            session["student_name"] = student["name"]

            flash("Student login successful!")

            return redirect(url_for("student_dashboard"))

        flash("Invalid email or password.")

    return render_template("login.html")


# Admin Add Event
@app.route("/add-event", methods=["GET", "POST"])
@admin_required
def add_event():

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        event_date = request.form["event_date"]
        location = request.form["location"]

        conn = get_db_connection()

        conn.execute(
            """INSERT INTO events
               (title, description, event_date, location)
               VALUES (?, ?, ?, ?)""",
            (title, description, event_date, location)
        )

        conn.commit()
        conn.close()

        flash("Event added successfully!")

        return redirect(url_for("events"))

    return render_template("add_event.html")


# View Campus Events
@app.route("/events")
def events():

    conn = get_db_connection()

    all_events = conn.execute(
        "SELECT * FROM events ORDER BY event_date"
    ).fetchall()

    conn.close()

    return render_template(
        "events.html",
        events=all_events
    )


# Student Attendance Page
@app.route("/attendance")
def attendance():

    if "student_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    conn = get_db_connection()

    all_events = conn.execute(
        "SELECT * FROM events ORDER BY event_date"
    ).fetchall()

    conn.close()

    return render_template(
        "attendance.html",
        events=all_events
    )


# Delete Event
@app.route("/delete-event/<int:event_id>", methods=["POST"])
@admin_required
def delete_event(event_id):

    conn = get_db_connection()

    conn.execute(
        "DELETE FROM attendance WHERE event_id = ?",
        (event_id,)
    )

    conn.execute(
        "DELETE FROM event_registrations WHERE event_id = ?",
        (event_id,)
    )

    conn.execute(
        "DELETE FROM events WHERE id = ?",
        (event_id,)
    )

    conn.commit()
    conn.close()

    flash("Event deleted successfully!")

    return redirect(url_for("events"))


# Mark Attendance
@app.route("/mark-attendance", methods=["POST"])
def mark_attendance():

    if "student_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    student_id = session["student_id"]
    event_id = request.form["event_id"]

    conn = get_db_connection()

    event = conn.execute(
        "SELECT id FROM events WHERE id = ?",
        (event_id,)
    ).fetchone()

    if event:

        existing = conn.execute(
            """SELECT id FROM attendance
               WHERE student_id = ? AND event_id = ?""",
            (student_id, event_id)
        ).fetchone()

        if existing:
            flash("You have already marked attendance for this event.")

        else:
            conn.execute(
                """INSERT INTO attendance
                   (student_id, event_id, status)
                   VALUES (?, ?, 'Present')""",
                (student_id, event_id)
            )

            conn.commit()
            flash("Attendance marked successfully!")

    else:
        flash("Invalid event.")

    conn.close()

    return redirect(url_for("attendance"))


# Admin Attendance Report
@app.route("/admin-attendance")
@admin_required
def admin_attendance():

    conn = get_db_connection()

    records = conn.execute("""
        SELECT students.name, students.email,
               events.title, attendance.status
        FROM attendance
        JOIN students ON attendance.student_id = students.id
        JOIN events ON attendance.event_id = events.id
        ORDER BY events.event_date DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_attendance.html",
        records=records
    )


# Student Certificate Page
@app.route("/certificates")
def certificates():

    if "student_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    conn = get_db_connection()

    student_certificates = conn.execute("""
        SELECT
            students.name,
            events.title,
            events.event_date,
            'C360-' || attendance.id AS certificate_id
        FROM attendance
        JOIN students
            ON attendance.student_id = students.id
        JOIN events
            ON attendance.event_id = events.id
        WHERE attendance.student_id = ?
          AND attendance.status = 'Present'
        ORDER BY events.event_date DESC
    """, (session["student_id"],)).fetchall()

    conn.close()

    return render_template(
        "certificate.html",
        certificates=student_certificates
    )


# Admin Dashboard
@app.route("/admin-dashboard")
@admin_required
def admin_dashboard():

    conn = get_db_connection()

    total_students = conn.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    total_events = conn.execute(
        "SELECT COUNT(*) FROM events"
    ).fetchone()[0]

    total_attendance = conn.execute(
        "SELECT COUNT(*) FROM attendance"
    ).fetchone()[0]

    total_certificates = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE status = 'Present'"
    ).fetchone()[0]

    # Recent students (registered_at is needed by the dashboard table)
    recent_students = conn.execute(
        """SELECT id, name, email, registered_at
           FROM students
           ORDER BY id DESC
           LIMIT 5"""
    ).fetchall()

    # Upcoming campus events
    upcoming_events = conn.execute(
        """SELECT * FROM events
           WHERE event_date >= date('now')
           ORDER BY event_date ASC
           LIMIT 5"""
    ).fetchall()

    # Monthly student registration analytics
    registration_data = conn.execute("""
        SELECT
            strftime('%Y-%m', registered_at) AS month,
            COUNT(*) AS total
        FROM students
        WHERE registered_at IS NOT NULL
        GROUP BY month
        ORDER BY month ASC
    """).fetchall()

    registration_labels = [
        row["month"] for row in registration_data
    ]

    registration_counts = [
        row["total"] for row in registration_data
    ]

    # Attendance analytics
    attendance_data = conn.execute("""
        SELECT status, COUNT(*) AS total
        FROM attendance
        GROUP BY status
    """).fetchall()

    attendance_status_counts = {
        "Present": 0,
        "Absent": 0
    }

    for row in attendance_data:
        if row["status"] in attendance_status_counts:
            attendance_status_counts[row["status"]] = row["total"]

    attendance_labels = list(attendance_status_counts.keys())
    attendance_counts = list(attendance_status_counts.values())

    # Names expected by the updated admin_dashboard.html
    student_months = registration_labels
    student_counts = registration_counts
    present_count = attendance_status_counts["Present"]
    absent_count = attendance_status_counts["Absent"]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        total_events=total_events,
        total_attendance=total_attendance,
        total_certificates=total_certificates,
        recent_students=recent_students,
        upcoming_events=upcoming_events,

        # New dashboard chart variables
        student_months=student_months,
        student_counts=student_counts,
        present_count=present_count,
        absent_count=absent_count,

        # Keep the earlier variable names too, for compatibility
        registration_labels=registration_labels,
        registration_counts=registration_counts,
        attendance_labels=attendance_labels,
        attendance_counts=attendance_counts
    )


# Admin Student Management
@app.route("/admin-students")
@admin_required
def admin_students():

    conn = get_db_connection()

    students = conn.execute(
        "SELECT id, name, email FROM students ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "admin_students.html",
        students=students
    )


# Admin Login
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()

        admin = conn.execute(
            "SELECT * FROM admins WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if admin and check_password_hash(
            admin["password"], password
        ):

            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]

            flash("Admin login successful!")

            return redirect(url_for("admin_dashboard"))

        flash("Invalid admin username or password.")

    return render_template("admin_login.html")


# Admin Logout
@app.route("/admin-logout")
def admin_logout():

    session.clear()

    flash("Admin logged out successfully.")

    return redirect(url_for("admin_login"))


# Student Logout
@app.route("/logout")
def logout():

    session.clear()

    flash("You have logged out successfully.")

    return redirect(url_for("home"))


# Student Profile
@app.route("/student-profile")
def student_profile():

    if "student_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    conn = get_db_connection()

    student = conn.execute(
        "SELECT id, name, email FROM students WHERE id = ?",
        (session["student_id"],)
    ).fetchone()

    attendance_records = conn.execute(
        """SELECT events.title, events.event_date,
                  events.location, attendance.status
           FROM attendance
           JOIN events ON attendance.event_id = events.id
           WHERE attendance.student_id = ?
           ORDER BY events.event_date DESC""",
        (session["student_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "student_profile.html",
        student=student,
        attendance_records=attendance_records
    )


# Student Dashboard
@app.route("/student-dashboard")
def student_dashboard():

    if "student_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    conn = get_db_connection()

    student = conn.execute(
        "SELECT id, name, email FROM students WHERE id = ?",
        (session["student_id"],)
    ).fetchone()

    conn.close()

    if student is None:
        session.clear()
        flash("Student account not found. Please login again.")
        return redirect(url_for("login"))

    return render_template(
        "student_dashboard.html",
        student=student
    )


# Event Registration Page
@app.route("/event-registration")
def event_registration():

    if "student_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    conn = get_db_connection()

    events = conn.execute(
        "SELECT * FROM events ORDER BY event_date ASC"
    ).fetchall()

    registrations = conn.execute(
        """SELECT event_id FROM event_registrations
           WHERE student_id = ?""",
        (session["student_id"],)
    ).fetchall()

    registered_event_ids = {
        registration["event_id"]
        for registration in registrations
    }

    conn.close()

    return render_template(
        "event_registration.html",
        events=events,
        registered_event_ids=registered_event_ids
    )


# Register for an Event
@app.route("/register-event/<int:event_id>", methods=["POST"])
def register_event(event_id):

    if "student_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    student_id = session["student_id"]

    conn = get_db_connection()

    try:

        event = conn.execute(
            "SELECT id, title FROM events WHERE id = ?",
            (event_id,)
        ).fetchone()

        if event is None:
            flash("Event not found.")

        else:

            existing = conn.execute(
                """SELECT id FROM event_registrations
                   WHERE student_id = ? AND event_id = ?""",
                (student_id, event_id)
            ).fetchone()

            if existing:
                flash("You are already registered for this event.")

            else:

                # Save Event Registration
                conn.execute(
                    """INSERT INTO event_registrations
                       (student_id, event_id)
                       VALUES (?, ?)""",
                    (student_id, event_id)
                )

                # Save Private Student Notification
                conn.execute(
                    """INSERT INTO notifications
                       (student_id, title, message)
                       VALUES (?, ?, ?)""",
                    (
                        student_id,
                        "Event Registration Successful!",
                        "You are successfully registered for "
                        + event["title"]
                    )
                )

                conn.commit()

                flash("Event registration successful!")

    finally:
        conn.close()

    return redirect(url_for("event_registration"))


# View Announcements
@app.route("/announcements")
def announcements():

    if "student_id" not in session and "admin_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    conn = get_db_connection()

    all_announcements = conn.execute(
        "SELECT * FROM announcements ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "announcements.html",
        announcements=all_announcements
    )


# Add Announcement (Admin Only)
@app.route("/add-announcement", methods=["POST"])
@admin_required
def add_announcement():

    title = request.form["title"]
    message = request.form["message"]

    conn = get_db_connection()

    conn.execute(
        """INSERT INTO announcements (title, message)
           VALUES (?, ?)""",
        (title, message)
    )

    conn.commit()
    conn.close()

    flash("Announcement published successfully!")

    return redirect(url_for("announcements"))


# Student Feedback Page
@app.route("/feedback")
def feedback():

    if "student_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    conn = get_db_connection()

    events = conn.execute(
        "SELECT id, title FROM events ORDER BY event_date ASC"
    ).fetchall()

    conn.close()

    return render_template(
        "feedback.html",
        events=events
    )


# Submit Student Feedback
@app.route("/submit-feedback", methods=["POST"])
def submit_feedback():

    if "student_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    event_id = request.form.get("event_id")
    rating = request.form.get("rating")
    feedback_text = request.form.get("feedback_text", "").strip()

    if not feedback_text or not rating:
        flash("Please complete all required fields.")
        return redirect(url_for("feedback"))

    try:
        rating = int(rating)
    except ValueError:
        flash("Invalid rating.")
        return redirect(url_for("feedback"))

    if rating not in range(1, 6):
        flash("Rating must be between 1 and 5.")
        return redirect(url_for("feedback"))

    conn = get_db_connection()

    if event_id:
        event = conn.execute(
            "SELECT id FROM events WHERE id = ?",
            (event_id,)
        ).fetchone()

        if event is None:
            conn.close()
            flash("Invalid event selected.")
            return redirect(url_for("feedback"))

    conn.execute(
        """INSERT INTO feedback
           (student_id, event_id, feedback_text, rating)
           VALUES (?, ?, ?, ?)""",
        (
            session["student_id"],
            int(event_id) if event_id else None,
            feedback_text,
            rating
        )
    )

    conn.commit()
    conn.close()

    flash("Feedback submitted successfully!")

    return redirect(url_for("feedback"))


# Admin Feedback Management
@app.route("/admin-feedback")
@admin_required
def admin_feedback():

    conn = get_db_connection()

    feedback_list = conn.execute("""
        SELECT
            feedback.id,
            feedback.feedback_text,
            feedback.rating,
            feedback.created_at,
            students.name AS student_name,
            students.email AS email,
            events.title AS event_title
        FROM feedback
        JOIN students
            ON feedback.student_id = students.id
        LEFT JOIN events
            ON feedback.event_id = events.id
        ORDER BY feedback.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_feedback.html",
        feedback_list=feedback_list
    )


# Admin Notifications Page
@app.route("/admin-notifications")
@admin_required
def admin_notifications():

    return render_template("admin_notifications.html")


# Send Notification to All Students
@app.route("/send-notification", methods=["POST"])
@admin_required
def send_notification():

    title = request.form.get("title", "").strip()
    message = request.form.get("message", "").strip()

    if not title or not message:
        flash("Please enter both title and message.")
        return redirect(url_for("admin_notifications"))

    conn = get_db_connection()

    try:

        students = conn.execute(
            "SELECT id FROM students"
        ).fetchall()

        for student in students:

            conn.execute(
                """INSERT INTO notifications
                   (student_id, title, message)
                   VALUES (?, ?, ?)""",
                (student["id"], title, message)
            )

        conn.commit()

    finally:
        conn.close()

    flash("Notification sent to all students!")

    return redirect(url_for("admin_notifications"))


# Student Notifications Page
@app.route("/notifications")
def notifications():

    if "student_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    conn = get_db_connection()

    all_notifications = conn.execute(
        """SELECT * FROM notifications
           WHERE student_id = ?
           ORDER BY id DESC""",
        (session["student_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "notifications.html",
        notifications=all_notifications
    )
@app.route("/my-registrations")
def my_registrations():

    if "student_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    conn = get_db_connection()

    registrations = conn.execute("""
        SELECT events.*
        FROM event_registrations
        JOIN events
        ON event_registrations.event_id = events.id
        WHERE event_registrations.student_id = ?
        ORDER BY events.event_date ASC
    """, (session["student_id"],)).fetchall()

    conn.close()

    return render_template(
        "my_registrations.html",
        registrations=registrations
    )
@app.route("/admin-event-registrations")
@admin_required
def admin_event_registrations():

    conn = get_db_connection()

    registrations = conn.execute("""
        SELECT
            students.name,
            students.email,
            events.title,
            events.event_date,
            event_registrations.registration_date
        FROM event_registrations
        JOIN students
            ON event_registrations.student_id = students.id
        JOIN events
            ON event_registrations.event_id = events.id
        ORDER BY event_registrations.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_event_registrations.html",
        registrations=registrations
    )

if __name__ == "__main__":
    app.run(debug=True)
