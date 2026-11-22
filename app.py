"""Online Examination System - Flask + MySQL"""
import os
from functools import wraps

import mysql.connector
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),   # set your MySQL password
    "database": os.environ.get("DB_NAME", "online_exam"),
}


# ---------------------- Database helper ----------------------
def query(sql, params=(), one=False, commit=False):
    """Run an SQL statement. Returns rows (SELECT) or last inserted id."""
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        if commit:
            conn.commit()
            return cur.lastrowid
        rows = cur.fetchall()
        return (rows[0] if rows else None) if one else rows
    finally:
        cur.close()
        conn.close()


# ---------------------- Auth decorators ----------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access only.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper


# ---------------------- Authentication ----------------------
@app.route("/")
def home():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html")
        exists = query("SELECT user_id FROM users WHERE username=%s OR email=%s",
                       (username, email), one=True)
        if exists:
            flash("Username or email already exists.", "error")
            return render_template("register.html")
        query("INSERT INTO users (username, email, password_hash) VALUES (%s,%s,%s)",
              (username, email, generate_password_hash(password)), commit=True)
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = query("SELECT * FROM users WHERE username=%s",
                     (request.form["username"].strip(),), one=True)
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


# ---------------------- Student side ----------------------
@app.route("/dashboard")
@login_required
def dashboard():
    exams = query("""SELECT e.*, COUNT(q.question_id) AS total_questions
                     FROM exams e LEFT JOIN questions q ON q.exam_id=e.exam_id
                     GROUP BY e.exam_id""")
    history = query("""SELECT r.result_id, e.title, r.score, r.total_questions,
                              r.percentage, r.submitted_at
                       FROM results r JOIN exams e ON e.exam_id=r.exam_id
                       WHERE r.user_id=%s ORDER BY r.submitted_at DESC""",
                    (session["user_id"],))
    return render_template("dashboard.html", exams=exams, history=history)


@app.route("/exam/<int:exam_id>")
@login_required
def exam(exam_id):
    exam_row = query("SELECT * FROM exams WHERE exam_id=%s", (exam_id,), one=True)
    if not exam_row:
        flash("Exam not found.", "error")
        return redirect(url_for("dashboard"))
    questions = query("SELECT * FROM questions WHERE exam_id=%s ORDER BY question_id",
                      (exam_id,))
    if not questions:
        flash("This exam has no questions yet.", "error")
        return redirect(url_for("dashboard"))
    return render_template("exam.html", exam=exam_row, questions=questions)


@app.route("/submit/<int:exam_id>", methods=["POST"])
@login_required
def submit(exam_id):
    questions = query("SELECT question_id, correct_option FROM questions WHERE exam_id=%s",
                      (exam_id,))
    total = len(questions)
    evaluated, score = [], 0

    # Automatic evaluation
    for q in questions:
        selected = request.form.get(f"q{q['question_id']}")
        correct = selected == q["correct_option"]
        score += 1 if correct else 0
        evaluated.append((q["question_id"], selected, correct))

    percentage = round(score * 100 / total, 2) if total else 0
    result_id = query("""INSERT INTO results (user_id, exam_id, score, total_questions, percentage)
                         VALUES (%s,%s,%s,%s,%s)""",
                      (session["user_id"], exam_id, score, total, percentage), commit=True)
    for qid, selected, correct in evaluated:
        query("""INSERT INTO answers (result_id, question_id, selected_option, is_correct)
                 VALUES (%s,%s,%s,%s)""", (result_id, qid, selected, correct), commit=True)
    return redirect(url_for("result", result_id=result_id))


@app.route("/result/<int:result_id>")
@login_required
def result(result_id):
    res = query("""SELECT r.*, e.title FROM results r JOIN exams e ON e.exam_id=r.exam_id
                   WHERE r.result_id=%s AND r.user_id=%s""",
                (result_id, session["user_id"]), one=True)
    if not res:
        flash("Result not found.", "error")
        return redirect(url_for("dashboard"))
    review = query("""SELECT q.question_text, q.option_a, q.option_b, q.option_c, q.option_d,
                             q.correct_option, a.selected_option, a.is_correct
                      FROM answers a JOIN questions q ON q.question_id=a.question_id
                      WHERE a.result_id=%s ORDER BY q.question_id""", (result_id,))
    return render_template("result.html", res=res, review=review)


# ---------------------- Admin: question management ----------------------
@app.route("/admin")
@admin_required
def admin():
    exams = query("SELECT * FROM exams")
    questions = query("""SELECT q.*, e.title FROM questions q
                         JOIN exams e ON e.exam_id=q.exam_id ORDER BY q.exam_id, q.question_id""")
    return render_template("admin.html", exams=exams, questions=questions)


@app.route("/admin/exam/add", methods=["POST"])
@admin_required
def add_exam():
    query("INSERT INTO exams (title, description, duration_minutes) VALUES (%s,%s,%s)",
          (request.form["title"], request.form["description"],
           int(request.form["duration"])), commit=True)
    flash("Exam created.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/question/add", methods=["POST"])
@admin_required
def add_question():
    f = request.form
    query("""INSERT INTO questions (exam_id, question_text, option_a, option_b,
                                    option_c, option_d, correct_option)
             VALUES (%s,%s,%s,%s,%s,%s,%s)""",
          (f["exam_id"], f["question_text"], f["option_a"], f["option_b"],
           f["option_c"], f["option_d"], f["correct_option"]), commit=True)
    flash("Question added.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/question/delete/<int:question_id>", methods=["POST"])
@admin_required
def delete_question(question_id):
    query("DELETE FROM questions WHERE question_id=%s", (question_id,), commit=True)
    flash("Question deleted.", "success")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=True)
