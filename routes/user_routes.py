import os
from io import BytesIO
from uuid import uuid4
from datetime import date

from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    current_app,
    send_file,
)
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database.db import get_connection
from groq_service import rate_submission, explain_topic
from youtube_service import search_youtube_videos

user_bp = Blueprint("user", __name__, url_prefix="/user")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "txt", "zip", "doc", "docx", "mp4"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_next_unlocked_day(user_id, course_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT MAX(day_number) AS last_completed_day
        FROM user_progress
        WHERE user_id = ? AND course_id = ? AND is_completed = 1
    """, (user_id, course_id))
    row = cursor.fetchone()
    conn.close()

    if row and row.last_completed_day:
        return row.last_completed_day + 1
    return 1


def generate_certificate_pdf(full_name, course_name, completed_at, badge_name):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setLineWidth(4)
    pdf.rect(30, 30, width - 60, height - 60)

    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(width / 2, height - 100, "Ramskon")

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawCentredString(width / 2, height - 145, "Certificate of Completion")

    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(width / 2, height - 220, "This certificate is proudly presented to")

    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(width / 2, height - 270, full_name)

    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(width / 2, height - 330, "for successfully completing the course")

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawCentredString(width / 2, height - 375, course_name)

    pdf.setFont("Helvetica", 15)
    pdf.drawCentredString(width / 2, height - 435, f"Badge Earned: {badge_name}")

    pdf.drawCentredString(width / 2, height - 470, f"Completion Date: {completed_at}")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(width / 2, 90, "Ramskon AI Learning Platform")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer


@user_bp.route("/dashboard")
def user_dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("role") != "user":
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()
    user_id = session["user_id"]

    cursor.execute("""
        SELECT COUNT(*) AS total_approved
        FROM course_requests
        WHERE user_id = ? AND status = 'approved'
    """, (user_id,))
    approved_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) AS completed_topics
        FROM user_progress
        WHERE user_id = ? AND is_completed = 1
    """, (user_id,))
    completed_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM course_topics ct
        JOIN course_requests cr ON ct.course_id = cr.course_id
        WHERE cr.user_id = ? AND cr.status = 'approved'
    """, (user_id,))
    total_topics = cursor.fetchone()[0]

    cursor.execute("""
        SELECT current_streak, best_streak, discipline_score, missed_days
        FROM users
        WHERE id = ?
    """, (user_id,))
    stats = cursor.fetchone()

    current_streak = 0
    best_streak = 0
    discipline_score = 0
    missed_days = 0

    if stats:
        current_streak = stats.current_streak or 0
        best_streak = stats.best_streak or 0
        discipline_score = stats.discipline_score or 0
        missed_days = stats.missed_days or 0

    progress_percent = 0
    if total_topics > 0:
        progress_percent = int((completed_count / total_topics) * 100)

    conn.close()

    return render_template(
        "user/dashboard.html",
        name=session.get("full_name"),
        approved_count=approved_count,
        completed_count=completed_count,
        total_topics=total_topics,
        progress_percent=progress_percent,
        current_streak=current_streak,
        best_streak=best_streak,
        discipline_score=discipline_score,
        missed_days=missed_days
    )


@user_bp.route("/courses", methods=["GET", "POST"])
def user_courses():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("role") != "user":
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        course_id = request.form["course_id"]
        user_id = session["user_id"]

        cursor.execute("""
            SELECT id FROM course_requests
            WHERE user_id = ? AND course_id = ?
        """, (user_id, course_id))
        existing_request = cursor.fetchone()

        if not existing_request:
            cursor.execute("""
                INSERT INTO course_requests (user_id, course_id, status)
                VALUES (?, ?, 'pending')
            """, (user_id, course_id))
            conn.commit()

    cursor.execute("SELECT id, course_name, description, duration_days FROM courses")
    courses = cursor.fetchall()

    cursor.execute("""
        SELECT cr.course_id, cr.status, c.course_name
        FROM course_requests cr
        JOIN courses c ON cr.course_id = c.id
        WHERE cr.user_id = ?
    """, (session["user_id"],))
    my_requests = cursor.fetchall()

    conn.close()

    return render_template(
        "user/courses.html",
        name=session.get("full_name"),
        courses=courses,
        my_requests=my_requests
    )


@user_bp.route("/approved-courses")
def approved_courses():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("role") != "user":
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.id,
            c.course_name,
            c.description,
            c.duration_days,
            ISNULL(cr.is_completed, 0) AS is_completed,
            cr.badge_name,
            cr.completed_at
        FROM course_requests cr
        JOIN courses c ON cr.course_id = c.id
        WHERE cr.user_id = ? AND cr.status = 'approved'
    """, (session["user_id"],))
    approved_courses = cursor.fetchall()

    conn.close()

    return render_template(
        "user/approved_courses.html",
        name=session.get("full_name"),
        approved_courses=approved_courses
    )


@user_bp.route("/course/<int:course_id>/roadmap")
def course_roadmap(course_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("role") != "user":
        return redirect(url_for("admin.admin_dashboard"))

    user_id = session["user_id"]
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM course_requests
        WHERE user_id = ? AND course_id = ? AND status = 'approved'
    """, (user_id, course_id))
    approved = cursor.fetchone()

    if not approved:
        conn.close()
        return "You are not approved for this course."

    cursor.execute("""
        SELECT course_name
        FROM courses
        WHERE id = ?
    """, (course_id,))
    course = cursor.fetchone()

    if not course:
        conn.close()
        return "Course not found."

    cursor.execute("""
        SELECT
            ct.id,
            ct.day_number,
            ct.topic_title,
            ISNULL(up.is_completed, 0) AS is_completed
        FROM course_topics ct
        LEFT JOIN user_progress up
            ON ct.id = up.topic_id
            AND up.user_id = ?
            AND up.course_id = ?
        WHERE ct.course_id = ?
        ORDER BY ct.day_number
    """, (user_id, course_id, course_id))
    topics = cursor.fetchall()

    if not topics:
        conn.close()
        return "This course roadmap is not added yet. Please add course topics first."

    next_unlocked_day = get_next_unlocked_day(user_id, course_id)
    total_days = len(topics)
    completed_days = sum(1 for t in topics if t.is_completed)
    progress_percent = int((completed_days / total_days) * 100) if total_days > 0 else 0

    conn.close()

    return render_template(
        "user/course_roadmap.html",
        name=session.get("full_name"),
        course_name=course.course_name,
        course_id=course_id,
        topics=topics,
        next_unlocked_day=next_unlocked_day,
        completed_days=completed_days,
        total_days=total_days,
        progress_percent=progress_percent
    )


@user_bp.route("/course/<int:course_id>/day/<int:day_number>", methods=["GET", "POST"])
def daily_topic(course_id, day_number):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("role") != "user":
        return redirect(url_for("admin.admin_dashboard"))

    user_id = session["user_id"]
    next_unlocked_day = get_next_unlocked_day(user_id, course_id)

    if day_number > next_unlocked_day:
        return "This day is locked. Complete previous days first."

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM course_requests
        WHERE user_id = ? AND course_id = ? AND status = 'approved'
    """, (user_id, course_id))
    approved = cursor.fetchone()

    if not approved:
        conn.close()
        return "You are not approved for this course."

    cursor.execute("""
        SELECT ct.id, ct.topic_title, ct.topic_description,
               ct.assignment_title, ct.assignment_description,
               c.course_name
        FROM course_topics ct
        JOIN courses c ON ct.course_id = c.id
        WHERE ct.course_id = ? AND ct.day_number = ?
    """, (course_id, day_number))
    topic = cursor.fetchone()

    if not topic:
        conn.close()
        return "Topic not found for this day."

    topic_ai = explain_topic(
        course_name=topic.course_name,
        day_number=day_number,
        topic_title=topic.topic_title,
        topic_description=topic.topic_description or "",
        assignment_title=topic.assignment_title or "",
        assignment_description=topic.assignment_description or ""
    )

    youtube_videos = []
    queries = topic_ai.get("youtube_search_queries", [])

    if not queries:
        queries = [
            f"{topic.topic_title} Telugu tutorial",
            f"{topic.course_name} {topic.topic_title} Telugu",
            f"{topic.topic_title} for beginners Telugu"
        ]

    for query in queries:
        try:
            results = search_youtube_videos(query, max_results=2)
            youtube_videos.extend(results)
        except Exception:
            pass

    unique_videos = []
    seen_links = set()

    for video in youtube_videos:
        if video["youtube_link"] not in seen_links:
            seen_links.add(video["youtube_link"])
            unique_videos.append(video)

    youtube_videos = unique_videos[:6]

    if request.method == "POST":
        submission_text = request.form.get("submission_text", "").strip()
        file = request.files.get("submission_file")
        saved_filename = None

        if file and file.filename:
            if not allowed_file(file.filename):
                conn.close()
                return "Invalid file type. Allowed: png, jpg, jpeg, pdf, txt, zip, doc, docx, mp4"

            original_name = secure_filename(file.filename)
            unique_name = f"{uuid4().hex}_{original_name}"
            upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
            file.save(upload_path)
            saved_filename = unique_name

        ai_result = rate_submission(
            course_name=topic.course_name,
            day_number=day_number,
            topic_title=topic.topic_title,
            assignment_title=topic.assignment_title or "",
            assignment_description=topic.assignment_description or "",
            submission_text=submission_text,
            submission_file=saved_filename or ""
        )

        ai_score = ai_result.get("score")
        ai_feedback = (
            f"Verdict: {ai_result.get('verdict', '')}\n"
            f"Strengths: {', '.join(ai_result.get('strengths', []))}\n"
            f"Missing Parts: {', '.join(ai_result.get('missing_parts', []))}\n"
            f"Improvement Tip: {ai_result.get('improvement_tip', '')}\n"
            f"Teacher Comment: {ai_result.get('teacher_comment', '')}"
        )

        cursor.execute("""
            SELECT id, submission_file FROM user_progress
            WHERE user_id = ? AND course_id = ? AND topic_id = ?
        """, (user_id, course_id, topic.id))
        existing = cursor.fetchone()

        if not existing:
            cursor.execute("""
                INSERT INTO user_progress
                (user_id, course_id, topic_id, day_number, is_completed, completed_at,
                 submission_text, submission_file, ai_score, ai_feedback, ai_evaluated_at)
                VALUES (?, ?, ?, ?, 1, GETDATE(), ?, ?, ?, ?, GETDATE())
            """, (
                user_id, course_id, topic.id, day_number,
                submission_text, saved_filename, ai_score, ai_feedback
            ))
        else:
            old_file = existing.submission_file
            final_file = saved_filename if saved_filename else old_file

            cursor.execute("""
                UPDATE user_progress
                SET is_completed = 1,
                    completed_at = GETDATE(),
                    submission_text = ?,
                    submission_file = ?,
                    ai_score = ?,
                    ai_feedback = ?,
                    ai_evaluated_at = GETDATE()
                WHERE id = ?
            """, (
                submission_text, final_file, ai_score, ai_feedback, existing.id
            ))

        cursor.execute("""
            SELECT current_streak, best_streak, discipline_score, last_completed_date, missed_days
            FROM users
            WHERE id = ?
        """, (user_id,))
        user_stats = cursor.fetchone()

        current_streak = user_stats.current_streak or 0
        best_streak = user_stats.best_streak or 0
        discipline_score = user_stats.discipline_score or 0
        last_date = user_stats.last_completed_date
        missed_days = user_stats.missed_days or 0

        today = date.today()

        if last_date:
            days_diff = (today - last_date).days
            if days_diff == 1:
                current_streak += 1
            elif days_diff > 1:
                missed_days += (days_diff - 1)
                current_streak = 1
        else:
            current_streak = 1

        if current_streak > best_streak:
            best_streak = current_streak

        discipline_score += 5
        if ai_score and ai_score >= 8:
            discipline_score += 2

        cursor.execute("""
            UPDATE users
            SET current_streak = ?,
                best_streak = ?,
                discipline_score = ?,
                last_completed_date = ?,
                missed_days = ?
            WHERE id = ?
        """, (current_streak, best_streak, discipline_score, today, missed_days, user_id))

        cursor.execute("""
            SELECT COUNT(*)
            FROM course_topics
            WHERE course_id = ?
        """, (course_id,))
        total_course_days = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM user_progress
            WHERE user_id = ? AND course_id = ? AND is_completed = 1
        """, (user_id, course_id))
        completed_course_days = cursor.fetchone()[0]

        if total_course_days > 0 and completed_course_days == total_course_days:
            badge_name = "Beginner Finisher"
            if discipline_score >= 20:
                badge_name = "Consistent Learner"
            if ai_score and ai_score >= 8:
                badge_name = "High Performer"

            cursor.execute("""
                UPDATE course_requests
                SET is_completed = 1,
                    completed_at = GETDATE(),
                    badge_name = ?
                WHERE user_id = ? AND course_id = ? AND status = 'approved'
            """, (badge_name, user_id, course_id))

        conn.commit()

    cursor.execute("""
        SELECT is_completed, submission_text, submission_file, ai_score, ai_feedback
        FROM user_progress
        WHERE user_id = ? AND course_id = ? AND topic_id = ?
    """, (user_id, course_id, topic.id))
    progress = cursor.fetchone()
    conn.close()

    is_completed = False
    submission_text = ""
    submission_file = ""
    ai_score = None
    ai_feedback = ""

    if progress:
        is_completed = bool(progress.is_completed)
        submission_text = progress.submission_text or ""
        submission_file = progress.submission_file or ""
        ai_score = progress.ai_score
        ai_feedback = progress.ai_feedback or ""

    return render_template(
        "user/daily_topic.html",
        name=session.get("full_name"),
        topic=topic,
        day_number=day_number,
        course_id=course_id,
        is_completed=is_completed,
        submission_text=submission_text,
        submission_file=submission_file,
        ai_score=ai_score,
        ai_feedback=ai_feedback,
        topic_ai=topic_ai,
        youtube_videos=youtube_videos
    )


@user_bp.route("/certificate/<int:course_id>")
def certificate(course_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("role") != "user":
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.full_name, c.course_name, cr.completed_at, cr.badge_name
        FROM course_requests cr
        JOIN users u ON cr.user_id = u.id
        JOIN courses c ON cr.course_id = c.id
        WHERE cr.user_id = ? AND cr.course_id = ? AND cr.is_completed = 1
    """, (session["user_id"], course_id))

    cert = cursor.fetchone()
    conn.close()

    if not cert:
        return "Certificate not available yet."

    return render_template("user/certificate.html", cert=cert, course_id=course_id)


@user_bp.route("/certificate/<int:course_id>/download")
def download_certificate(course_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("role") != "user":
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.full_name, c.course_name, cr.completed_at, cr.badge_name
        FROM course_requests cr
        JOIN users u ON cr.user_id = u.id
        JOIN courses c ON cr.course_id = c.id
        WHERE cr.user_id = ? AND cr.course_id = ? AND cr.is_completed = 1
    """, (session["user_id"], course_id))

    cert = cursor.fetchone()
    conn.close()

    if not cert:
        return "Certificate not available yet."

    pdf_buffer = generate_certificate_pdf(
        full_name=cert.full_name,
        course_name=cert.course_name,
        completed_at=str(cert.completed_at),
        badge_name=cert.badge_name or "Course Finisher"
    )

    safe_course_name = cert.course_name.replace(" ", "_")

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"{safe_course_name}_certificate.pdf",
        mimetype="application/pdf"
    )


@user_bp.route("/progress")
def progress():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("role") != "user":
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.course_name, up.day_number, ct.topic_title,
               up.is_completed, up.completed_at, up.submission_text,
               up.submission_file, up.ai_score, up.ai_feedback
        FROM user_progress up
        JOIN courses c ON up.course_id = c.id
        JOIN course_topics ct ON up.topic_id = ct.id
        WHERE up.user_id = ?
        ORDER BY c.course_name, up.day_number
    """, (session["user_id"],))
    progress_data = cursor.fetchall()

    conn.close()

    return render_template(
        "user/progress.html",
        name=session.get("full_name"),
        progress_data=progress_data
    )