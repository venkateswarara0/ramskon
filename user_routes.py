from flask import Blueprint, render_template, session, redirect, url_for, request
from database.db import get_connection

user_bp = Blueprint("user", __name__, url_prefix="/user")


@user_bp.route("/dashboard")
def user_dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("role") != "user":
        return redirect(url_for("auth.login"))

    return render_template("user_dashboard.html", user_name=session.get("full_name"))


@user_bp.route("/courses")
def user_courses():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("role") != "user":
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, duration_days, created_at, course_name, description, category
        FROM courses
        ORDER BY id
    """)
    courses = cursor.fetchall()

    cursor.execute("""
        SELECT course_id, status
        FROM course_requests
        WHERE user_id = %s
    """, (user_id,))
    request_rows = cursor.fetchall()

    requested_courses = {row[0]: row[1] for row in request_rows}

    conn.close()

    return render_template(
        "user_courses.html",
        courses=courses,
        requested_courses=requested_courses,
        user_name=session.get("full_name", "User")
    )


@user_bp.route("/request-course", methods=["POST"])
def request_course():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("role") != "user":
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    course_id = request.form.get("course_id")

    if not course_id:
        return "Course ID is missing", 400

    try:
        course_id = int(course_id)
    except ValueError:
        return "Invalid course ID", 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM course_requests
        WHERE user_id = %s AND course_id = %s
    """, (user_id, course_id))
    existing_request = cursor.fetchone()

    if existing_request:
        conn.close()
        return redirect(url_for("user.user_courses"))

    cursor.execute("""
        INSERT INTO course_requests (user_id, course_id, status)
        VALUES (%s, %s, %s)
    """, (user_id, course_id, "pending"))

    conn.commit()
    conn.close()

    return redirect(url_for("user.user_courses"))