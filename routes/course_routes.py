from flask import Blueprint, render_template, session, redirect, url_for, request
from database.db import get_connection

course_bp = Blueprint("course", __name__, url_prefix="/course")


@course_bp.route("/list")
def course_list():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, course_name, description, duration_days FROM courses")
    courses = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/manage_courses.html",
        name=session.get("full_name"),
        courses=courses
    )


@course_bp.route("/add", methods=["GET", "POST"])
def add_course():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role") != "admin":
        return redirect(url_for("user.user_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        course_name = request.form["course_name"]
        description = request.form["description"]
        category = request.form["category"]
        duration_days = request.form["duration_days"]

        cursor.execute("""
            INSERT INTO courses (course_name, description, category, duration_days)
            VALUES (%s, %s, %s, %s)
        """, (course_name, description, category, duration_days))
        conn.commit()
        conn.close()
        return redirect(url_for("course.course_list"))

    conn.close()
    return render_template("admin/add_course.html", name=session.get("full_name"))


@course_bp.route("/edit/<int:course_id>", methods=["GET", "POST"])
def edit_course(course_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role") != "admin":
        return redirect(url_for("user.user_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        course_name = request.form["course_name"]
        description = request.form["description"]
        category = request.form["category"]
        duration_days = request.form["duration_days"]

        cursor.execute("""
            UPDATE courses
            SET course_name = %s, description = %s,
                category = %s, duration_days = %s
            WHERE id = %s
        """, (course_name, description, category, duration_days, course_id))
        conn.commit()
        conn.close()
        return redirect(url_for("course.course_list"))

    cursor.execute("""
        SELECT id, course_name, description, category, duration_days
        FROM courses WHERE id = %s
    """, (course_id,))
    course = cursor.fetchone()
    conn.close()

    return render_template(
        "admin/edit_course.html",
        name=session.get("full_name"),
        course=course
    )


@course_bp.route("/delete/<int:course_id>")
def delete_course(course_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role") != "admin":
        return redirect(url_for("user.user_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM course_topics WHERE course_id = %s", (course_id,))
    cursor.execute("DELETE FROM course_requests WHERE course_id = %s", (course_id,))
    cursor.execute("DELETE FROM courses WHERE id = %s", (course_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("course.course_list"))


@course_bp.route("/<int:course_id>/topics")
def manage_topics(course_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role") != "admin":
        return redirect(url_for("user.user_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT course_name FROM courses WHERE id = %s
    """, (course_id,))
    course = cursor.fetchone()

    cursor.execute("""
        SELECT id, day_number, topic_title, topic_description
        FROM course_topics
        WHERE course_id = %s
        ORDER BY day_number
    """, (course_id,))
    topics = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/manage_topics.html",
        name=session.get("full_name"),
        course=course,
        course_id=course_id,
        topics=topics
    )


@course_bp.route("/<int:course_id>/topics/add", methods=["GET", "POST"])
def add_topic(course_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role") != "admin":
        return redirect(url_for("user.user_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        day_number = request.form["day_number"]
        topic_title = request.form["topic_title"]
        topic_description = request.form["topic_description"]
        assignment_title = request.form.get("assignment_title", "")
        assignment_description = request.form.get("assignment_description", "")

        cursor.execute("""
            INSERT INTO course_topics
            (course_id, day_number, topic_title, topic_description,
             assignment_title, assignment_description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (course_id, day_number, topic_title, topic_description,
              assignment_title, assignment_description))
        conn.commit()
        conn.close()
        return redirect(url_for("course.manage_topics", course_id=course_id))

    conn.close()
    return render_template(
        "admin/add_topic.html",
        name=session.get("full_name"),
        course_id=course_id
    )


@course_bp.route("/<int:course_id>/topics/edit/<int:topic_id>", methods=["GET", "POST"])
def edit_topic(course_id, topic_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role") != "admin":
        return redirect(url_for("user.user_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        day_number = request.form["day_number"]
        topic_title = request.form["topic_title"]
        topic_description = request.form["topic_description"]
        assignment_title = request.form.get("assignment_title", "")
        assignment_description = request.form.get("assignment_description", "")

        cursor.execute("""
            UPDATE course_topics
            SET day_number = %s, topic_title = %s, topic_description = %s,
                assignment_title = %s, assignment_description = %s
            WHERE id = %s AND course_id = %s
        """, (day_number, topic_title, topic_description,
              assignment_title, assignment_description,
              topic_id, course_id))
        conn.commit()
        conn.close()
        return redirect(url_for("course.manage_topics", course_id=course_id))

    cursor.execute("""
        SELECT id, day_number, topic_title, topic_description,
               assignment_title, assignment_description
        FROM course_topics WHERE id = %s
    """, (topic_id,))
    topic = cursor.fetchone()
    conn.close()

    return render_template(
        "admin/edit_topic.html",
        name=session.get("full_name"),
        course_id=course_id,
        topic=topic
    )


@course_bp.route("/<int:course_id>/topics/delete/<int:topic_id>")
def delete_topic(course_id, topic_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role") != "admin":
        return redirect(url_for("user.user_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM course_topics WHERE id = %s", (topic_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("course.manage_topics", course_id=course_id))