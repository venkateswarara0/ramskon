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
            VALUES (%s, %s, %s, 'user', 0)
        """, (full_name, email, password_hash))

        conn.commit()
        conn.close()
        return redirect(url_for("auth.login"))

    return render_template("register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        print("LOGIN ATTEMPT:", email)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, full_name, email, password_hash, role, is_approved
            FROM users
            WHERE email = %s
        """, (email,))

        user = cursor.fetchone()
        conn.close()

        if not user:
            return "User not found."

        if not check_password_hash(user[3], password):
            return "Wrong password."

        session["user_id"] = user[0]
        session["full_name"] = user[1]
        session["email"] = user[2]
        session["role"] = user[4]
        session["is_approved"] = bool(user[5])

        if user[4] == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        else:
            return redirect(url_for("user.user_dashboard"))

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))