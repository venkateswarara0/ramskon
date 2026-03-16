from flask import Blueprint, render_template, session, redirect, url_for, request
from database.db import get_connection

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/dashboard")
def admin_dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("role") != "admin":
        return redirect(url_for("user.user_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM course_requests WHERE status = 'pending'")
    pending_requests = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM course_requests WHERE status = 'approved'")
    approved_requests = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user_progress WHERE is_completed = 1")
    completed_topics = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin/dashboard.html",
        name=session.get("full_name"),
        total_users=total_users,
        pending_requests=pending_requests,
        approved_requests=approved_requests,
        completed_topics=completed_topics
    )

@admin_bp.route("/pending-requests", methods=["GET", "POST"])
def pending_requests():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("role") != "admin":
        return redirect(url_for("user.user_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        request_id = request.form["request_id"]
        action = request.form["action"]

        if action == "approve":
            cursor.execute("""
                UPDATE course_requests
                SET status = 'approved', approved_at = GETDATE()
                WHERE id = ?
            """, (request_id,))
        elif action == "reject":
            cursor.execute("""
                UPDATE course_requests
                SET status = 'rejected'
                WHERE id = ?
            """, (request_id,))

        conn.commit()

    cursor.execute("""
        SELECT cr.id, u.full_name, u.email, c.course_name, cr.status, cr.requested_at
        FROM course_requests cr
        JOIN users u ON cr.user_id = u.id
        JOIN courses c ON cr.course_id = c.id
        WHERE cr.status = 'pending'
        ORDER BY cr.requested_at DESC
    """)
    requests_data = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/pending_requests.html",
        name=session.get("full_name"),
        requests_data=requests_data
    )

@admin_bp.route("/submission-reviews")
def submission_reviews():
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
            up.day_number,
            ct.topic_title,
            up.submission_text,
            up.submission_file,
            up.ai_score,
            up.ai_feedback,
            up.completed_at
        FROM user_progress up
        JOIN users u ON up.user_id = u.id
        JOIN courses c ON up.course_id = c.id
        JOIN course_topics ct ON up.topic_id = ct.id
        WHERE up.is_completed = 1
        ORDER BY up.completed_at DESC
    """)
    submissions = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/submission_reviews.html",
        name=session.get("full_name"),
        submissions=submissions
    )