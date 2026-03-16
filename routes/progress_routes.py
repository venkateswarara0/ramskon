from flask import Blueprint, render_template, session, redirect, url_for
from database.db import get_connection

progress_bp = Blueprint("progress", __name__, url_prefix="/progress")


@progress_bp.route("/overview")
def progress_overview():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.id,
            c.course_name,
            COUNT(ct.id) AS total_topics,
            COUNT(up.id) AS completed_topics
        FROM course_requests cr
        JOIN courses c ON cr.course_id = c.id
        JOIN course_topics ct ON ct.course_id = c.id
        LEFT JOIN user_progress up
            ON up.topic_id = ct.id
            AND up.user_id = %s
            AND up.is_completed = TRUE
        WHERE cr.user_id = %s AND cr.status = 'approved'
        GROUP BY c.id, c.course_name
    """, (user_id, user_id))
    courses_progress = cursor.fetchall()

    conn.close()

    return render_template(
        "user/progress.html",
        name=session.get("full_name"),
        courses_progress=courses_progress
    )


@progress_bp.route("/course/<int:course_id>")
def course_progress(course_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT course_name FROM courses WHERE id = %s
    """, (course_id,))
    course = cursor.fetchone()

    if not course:
        conn.close()
        return "Course not found."

    cursor.execute("""
        SELECT
            ct.day_number,
            ct.topic_title,
            COALESCE(up.is_completed, FALSE) AS is_completed,
            up.completed_at,
            up.ai_score,
            up.submission_text
        FROM course_topics ct
        LEFT JOIN user_progress up
            ON ct.id = up.topic_id
            AND up.user_id = %s
            AND up.course_id = %s
        WHERE ct.course_id = %s
        ORDER BY ct.day_number
    """, (user_id, course_id, course_id))
    topics = cursor.fetchall()

    total = len(topics)
    completed = sum(1 for t in topics if t[2])
    percent = int((completed / total) * 100) if total > 0 else 0

    conn.close()

    return render_template(
        "user/course_progress.html",
        name=session.get("full_name"),
        course_name=course[0],
        course_id=course_id,
        topics=topics,
        total=total,
        completed=completed,
        percent=percent
    )


@progress_bp.route("/admin/all-users")
def admin_all_progress():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role") != "admin":
        return redirect(url_for("user.user_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            u.full_name,
            u.email,
            c.course_name,
            COUNT(ct.id) AS total_topics,
            COUNT(up.id) AS completed_topics
        FROM users u
        JOIN course_requests cr ON cr.user_id = u.id
        JOIN courses c ON cr.course_id = c.id
        JOIN course_topics ct ON ct.course_id = c.id
        LEFT JOIN user_progress up
            ON up.topic_id = ct.id
            AND up.user_id = u.id
            AND up.is_completed = TRUE
        WHERE cr.status = 'approved' AND u.role = 'user'
        GROUP BY u.full_name, u.email, c.course_name
        ORDER BY u.full_name
    """)
    all_progress = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/all_progress.html",
        name=session.get("full_name"),
        all_progress=all_progress
    )


@progress_bp.route("/admin/reports")
def admin_reports():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role") != "admin":
        return redirect(url_for("user.user_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.course_name,
            COUNT(DISTINCT cr.user_id) AS total_enrolled,
            COUNT(DISTINCT CASE WHEN cr.is_completed = TRUE
                THEN cr.user_id END) AS total_completed
        FROM courses c
        LEFT JOIN course_requests cr ON cr.course_id = c.id
        WHERE cr.status = 'approved'
        GROUP BY c.course_name
        ORDER BY total_enrolled DESC
    """)
    course_reports = cursor.fetchall()

    cursor.execute("""
        SELECT
            u.full_name,
            u.email,
            COUNT(up.id) AS topics_completed,
            u.current_streak,
            u.discipline_score
        FROM users u
        LEFT JOIN user_progress up
            ON up.user_id = u.id AND up.is_completed = TRUE
        WHERE u.role = 'user'
        GROUP BY u.full_name, u.email, u.current_streak, u.discipline_score
        ORDER BY topics_completed DESC
    """)
    user_reports = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/reports.html",
        name=session.get("full_name"),
        course_reports=course_reports,
        user_reports=user_reports
    )