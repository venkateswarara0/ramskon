from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_connection

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def home():
    return render_template("index.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]

        password_hash = generate_password_hash(password)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return "Email already registered."

        cursor.execute("""
            INSERT INTO users (full_name, email, password_hash, role, is_approved)
            VALUES (%s, %s, %s, %s, %s)
        """, (full_name, email, password_hash, "user", False))

        conn.commit()
        conn.close()

        return redirect(url_for("auth.login"))

    return render_template("register.html")