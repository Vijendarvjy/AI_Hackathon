import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (  # pyright: ignore[reportMissingImports]
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "instance", "hackathon.db")

# Hackathon configuration
THEME_TITLE = "Meri Samasya, Mera Samadhan (My Problem, My Solution)"
THEME_DESCRIPTION = (
    "Students solve a real problem from their own home, school, or village. "
    "Judges reward thinking about the problem over technical polish."
)

TRACKS = [
    {
        "name": "Safe and healthy communities",
        "examples": "Medicine reminder for a grandparent, clean-water checklist, first-aid game",
    },
    {
        "name": "Farming and local livelihoods",
        "examples": "Crop-price record, a small seller’s profit calculator, pest identification guide",
    },
    {
        "name": "Climate and environment",
        "examples": "Water-tank overflow alert, waste-sorting game, heat-safety awareness tool",
    },
    {
        "name": "Better learning at school",
        "examples": "Local-language maths game, attendance tracker, science model with sensors",
    },
    {
        "name": "Inclusion and girls’ safety",
        "examples": "Tool for a classmate with a disability, safe-route map, story game about rights",
    },
    {
        "name": "AI for good (optional, Class 8-9)",
        "examples": "Simple image or sound classifier, plus a discussion of where it could go wrong",
    },
]

JUDGING_PARAMETERS = [
    {
        "key": "problem_understanding",
        "label": "Problem Understanding",
        "description": "Clarity and depth of understanding of the real-life problem (Meri Samasya).",
    },
    {
        "key": "solution_relevance",
        "label": "Solution Relevance & Impact",
        "description": "How well the solution addresses the problem and benefits the community (Mera Samadhan).",
    },
    {
        "key": "creativity",
        "label": "Creativity & Innovation",
        "description": "Originality and thoughtful approach to solving the problem.",
    },
    {
        "key": "feasibility",
        "label": "Feasibility & Implementation",
        "description": "Practicality and how realistically the idea can be implemented or demonstrated.",
    },
    {
        "key": "presentation",
        "label": "Presentation & Explanation",
        "description": "Clarity of explanation, communication, and ability to discuss limitations or improvements.",
    },
]

MIN_SCORE = 1
MAX_SCORE = 10

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'judge')),
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_number TEXT UNIQUE NOT NULL,
            team_type TEXT NOT NULL CHECK(team_type IN ('solo', 'group')),
            track TEXT NOT NULL,
            problem_title TEXT NOT NULL,
            problem_description TEXT NOT NULL,
            school_name TEXT NOT NULL,
            leader_name TEXT NOT NULL,
            leader_class TEXT NOT NULL,
            leader_contact TEXT,
            leader_email TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_id INTEGER NOT NULL,
            member_name TEXT NOT NULL,
            member_class TEXT NOT NULL,
            FOREIGN KEY(registration_id) REFERENCES registrations(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_id INTEGER NOT NULL,
            judge_id INTEGER NOT NULL,
            problem_understanding INTEGER NOT NULL,
            solution_relevance INTEGER NOT NULL,
            creativity INTEGER NOT NULL,
            feasibility INTEGER NOT NULL,
            presentation INTEGER NOT NULL,
            comments TEXT,
            total_score INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(registration_id, judge_id),
            FOREIGN KEY(registration_id) REFERENCES registrations(id) ON DELETE CASCADE,
            FOREIGN KEY(judge_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )

    # Seed default admin and judge accounts if missing
    now = datetime.utcnow().isoformat(timespec="seconds")
    existing_admin = db.execute(
        "SELECT id FROM users WHERE username = ?", ("admin",)
    ).fetchone()
    if not existing_admin:
        db.execute(
            "INSERT INTO users (username, password_hash, role, name, created_at) VALUES (?, ?, ?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "admin", "Administrator", now),
        )
    existing_judge = db.execute(
        "SELECT id FROM users WHERE username = ?", ("judge",)
    ).fetchone()
    if not existing_judge:
        db.execute(
            "INSERT INTO users (username, password_hash, role, name, created_at) VALUES (?, ?, ?, ?, ?)",
            ("judge", generate_password_hash("judge123"), "judge", "Demo Judge", now),
        )
    db.commit()


def generate_registration_number():
    db = get_db()
    year = datetime.utcnow().year
    prefix = f"AIH-{year}-"
    row = db.execute(
        "SELECT registration_number FROM registrations WHERE registration_number LIKE ? ORDER BY id DESC LIMIT 1",
        (f"{prefix}%",),
    ).fetchone()
    if row:
        try:
            last_seq = int(row["registration_number"].split("-")[-1])
        except (ValueError, IndexError):
            last_seq = 0
    else:
        last_seq = 0
    return f"{prefix}{last_seq + 1:04d}"


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = session.get("user")
            if not user:
                flash("Please log in to continue.", "error")
                target = "admin_login" if role == "admin" else "judge_login" if role == "judge" else "index"
                return redirect(url_for(target))
            if role and user.get("role") != role:
                flash("You do not have access to that page.", "error")
                return redirect(url_for("index"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


@app.before_request
def ensure_db():
    init_db()


@app.context_processor
def inject_globals():
    return {
        "theme_title": THEME_TITLE,
        "theme_description": THEME_DESCRIPTION,
        "tracks": TRACKS,
        "judging_parameters": JUDGING_PARAMETERS,
        "current_user": session.get("user"),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        team_type = (request.form.get("team_type") or "").strip()
        track = (request.form.get("track") or "").strip()
        problem_title = (request.form.get("problem_title") or "").strip()
        problem_description = (request.form.get("problem_description") or "").strip()
        school_name = (request.form.get("school_name") or "").strip()
        leader_name = (request.form.get("leader_name") or "").strip()
        leader_class = (request.form.get("leader_class") or "").strip()
        leader_contact = (request.form.get("leader_contact") or "").strip()
        leader_email = (request.form.get("leader_email") or "").strip()

        errors = []
        if team_type not in {"solo", "group"}:
            errors.append("Please select a valid registration type (solo or group).")
        valid_track_names = {t["name"] for t in TRACKS}
        if track not in valid_track_names:
            errors.append("Please select a valid track.")
        if not problem_title:
            errors.append("Problem/solution title is required.")
        if not problem_description:
            errors.append("Problem description is required.")
        if not school_name:
            errors.append("School name is required.")
        if not leader_name:
            errors.append("Leader/student name is required.")
        if not leader_class:
            errors.append("Leader/student class is required.")

        members = []
        if team_type == "group":
            member_indices = set()
            for key in request.form.keys():
                if key.startswith("member_") and key.endswith("_name"):
                    middle = key[len("member_") : -len("_name")]
                    if middle.isdigit():
                        member_indices.add(int(middle))
            for i in sorted(member_indices):
                name = (request.form.get(f"member_{i}_name") or "").strip()
                cls = (request.form.get(f"member_{i}_class") or "").strip()
                if name or cls:
                    if not name or not cls:
                        errors.append(f"Member {i}: please provide both name and class, or leave both blank.")
                    else:
                        members.append((name, cls))
            # Group registration must include at least one additional member besides the leader.
            if len(members) < 1:
                errors.append("Group registration must include at least one additional member besides the leader.")
        else:
            members = []

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "register.html",
                form=request.form,
            )

        db = get_db()
        reg_no = generate_registration_number()
        now = datetime.utcnow().isoformat(timespec="seconds")
        cur = db.execute(
            """
            INSERT INTO registrations
            (registration_number, team_type, track, problem_title, problem_description,
             school_name, leader_name, leader_class, leader_contact, leader_email, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reg_no,
                team_type,
                track,
                problem_title,
                problem_description,
                school_name,
                leader_name,
                leader_class,
                leader_contact or None,
                leader_email or None,
                now,
            ),
        )
        reg_id = cur.lastrowid
        for m_name, m_class in members:
            db.execute(
                "INSERT INTO team_members (registration_id, member_name, member_class) VALUES (?, ?, ?)",
                (reg_id, m_name, m_class),
            )
        db.commit()
        return redirect(url_for("register_success", reg_no=reg_no))

    return render_template("register.html", form={})


@app.route("/register/success/<reg_no>")
def register_success(reg_no):
    db = get_db()
    reg = db.execute(
        "SELECT * FROM registrations WHERE registration_number = ?", (reg_no,)
    ).fetchone()
    if not reg:
        flash("Registration not found.", "error")
        return redirect(url_for("index"))
    members = db.execute(
        "SELECT member_name, member_class FROM team_members WHERE registration_id = ? ORDER BY id",
        (reg["id"],),
    ).fetchall()
    return render_template("register_success.html", registration=reg, members=members)


def authenticate(username, password, role):
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username = ? AND role = ?", (username, role)
    ).fetchone()
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = authenticate(username, password, "admin")
        if user:
            session["user"] = {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "name": user["name"],
            }
            flash("Welcome, admin.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials.", "error")
    return render_template("login.html", role="admin")


@app.route("/judge/login", methods=["GET", "POST"])
def judge_login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = authenticate(username, password, "judge")
        if user:
            session["user"] = {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "name": user["name"],
            }
            flash(f"Welcome, {user['name']}.", "success")
            return redirect(url_for("judge_dashboard"))
        flash("Invalid judge credentials.", "error")
    return render_template("login.html", role="judge")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/admin")
@login_required(role="admin")
def admin_dashboard():
    db = get_db()
    registrations = db.execute(
        "SELECT * FROM registrations ORDER BY created_at DESC, id DESC"
    ).fetchall()
    members_by_reg = {}
    for r in registrations:
        members_by_reg[r["id"]] = db.execute(
            "SELECT member_name, member_class FROM team_members WHERE registration_id = ? ORDER BY id",
            (r["id"],),
        ).fetchall()

    # Aggregate evaluation results per registration
    results = db.execute(
        """
        SELECT r.id, r.registration_number, r.team_type, r.track, r.problem_title,
               r.school_name, r.leader_name,
               COUNT(e.id) as eval_count,
               ROUND(AVG(e.total_score), 2) as avg_total,
               ROUND(AVG(e.problem_understanding), 2) as avg_problem_understanding,
               ROUND(AVG(e.solution_relevance), 2) as avg_solution_relevance,
               ROUND(AVG(e.creativity), 2) as avg_creativity,
               ROUND(AVG(e.feasibility), 2) as avg_feasibility,
               ROUND(AVG(e.presentation), 2) as avg_presentation
        FROM registrations r
        LEFT JOIN evaluations e ON e.registration_id = r.id
        GROUP BY r.id
        ORDER BY avg_total IS NULL, avg_total DESC, r.created_at ASC
        """
    ).fetchall()

    judges = db.execute(
        "SELECT id, username, name, created_at FROM users WHERE role = 'judge' ORDER BY created_at DESC"
    ).fetchall()
    stats = {
        "total_registrations": len(registrations),
        "solo": sum(1 for r in registrations if r["team_type"] == "solo"),
        "group": sum(1 for r in registrations if r["team_type"] == "group"),
        "evaluated": sum(1 for r in results if r["eval_count"] and r["eval_count"] > 0),
        "judges": len(judges),
    }
    return render_template(
        "admin_dashboard.html",
        registrations=registrations,
        members_by_reg=members_by_reg,
        results=results,
        judges=judges,
        stats=stats,
    )


@app.route("/admin/judges", methods=["GET", "POST"])
@login_required(role="admin")
def admin_judges():
    db = get_db()
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        errors = []
        if not name:
            errors.append("Judge name is required.")
        if not username:
            errors.append("Username is required.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if username:
            existing = db.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if existing:
                errors.append("That username is already taken.")
        if errors:
            for e in errors:
                flash(e, "error")
        else:
            now = datetime.utcnow().isoformat(timespec="seconds")
            db.execute(
                "INSERT INTO users (username, password_hash, role, name, created_at) VALUES (?, ?, 'judge', ?, ?)",
                (username, generate_password_hash(password), name, now),
            )
            db.commit()
            flash(f"Judge '{name}' created successfully.", "success")
            return redirect(url_for("admin_judges"))

    judges = db.execute(
        "SELECT id, username, name, created_at FROM users WHERE role = 'judge' ORDER BY created_at DESC"
    ).fetchall()
    return render_template("admin_judges.html", judges=judges)


@app.route("/judge")
@login_required(role="judge")
def judge_dashboard():
    db = get_db()
    judge_id = session["user"]["id"]
    rows = db.execute(
        """
        SELECT r.*, e.id as evaluation_id, e.total_score, e.updated_at as eval_updated_at
        FROM registrations r
        LEFT JOIN evaluations e ON e.registration_id = r.id AND e.judge_id = ?
        ORDER BY e.id IS NULL DESC, r.created_at ASC
        """,
        (judge_id,),
    ).fetchall()
    members_by_reg = {}
    for r in rows:
        members_by_reg[r["id"]] = db.execute(
            "SELECT member_name, member_class FROM team_members WHERE registration_id = ? ORDER BY id",
            (r["id"],),
        ).fetchall()
    pending = sum(1 for r in rows if not r["evaluation_id"])
    completed = sum(1 for r in rows if r["evaluation_id"])
    return render_template(
        "judge_dashboard.html",
        registrations=rows,
        members_by_reg=members_by_reg,
        pending=pending,
        completed=completed,
    )


@app.route("/judge/evaluate/<int:registration_id>", methods=["GET", "POST"])
@login_required(role="judge")
def evaluate(registration_id):
    db = get_db()
    judge_id = session["user"]["id"]
    registration = db.execute(
        "SELECT * FROM registrations WHERE id = ?", (registration_id,)
    ).fetchone()
    if not registration:
        flash("Registration not found.", "error")
        return redirect(url_for("judge_dashboard"))

    members = db.execute(
        "SELECT member_name, member_class FROM team_members WHERE registration_id = ? ORDER BY id",
        (registration_id,),
    ).fetchall()
    existing = db.execute(
        "SELECT * FROM evaluations WHERE registration_id = ? AND judge_id = ?",
        (registration_id, judge_id),
    ).fetchone()

    if request.method == "POST":
        scores = {}
        errors = []
        for p in JUDGING_PARAMETERS:
            raw = (request.form.get(p["key"]) or "").strip()
            try:
                val = int(raw)
            except ValueError:
                errors.append(f"{p['label']}: please enter a number between {MIN_SCORE} and {MAX_SCORE}.")
                continue
            if val < MIN_SCORE or val > MAX_SCORE:
                errors.append(f"{p['label']}: score must be between {MIN_SCORE} and {MAX_SCORE}.")
            scores[p["key"]] = val
        comments = (request.form.get("comments") or "").strip()

        if errors:
            for e in errors:
                flash(e, "error")
        else:
            total = sum(scores[p["key"]] for p in JUDGING_PARAMETERS)
            now = datetime.utcnow().isoformat(timespec="seconds")
            if existing:
                db.execute(
                    """
                    UPDATE evaluations SET
                        problem_understanding = ?, solution_relevance = ?, creativity = ?,
                        feasibility = ?, presentation = ?, comments = ?, total_score = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        scores["problem_understanding"],
                        scores["solution_relevance"],
                        scores["creativity"],
                        scores["feasibility"],
                        scores["presentation"],
                        comments or None,
                        total,
                        now,
                        existing["id"],
                    ),
                )
                flash("Evaluation updated successfully.", "success")
            else:
                db.execute(
                    """
                    INSERT INTO evaluations
                    (registration_id, judge_id, problem_understanding, solution_relevance, creativity,
                     feasibility, presentation, comments, total_score, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        registration_id,
                        judge_id,
                        scores["problem_understanding"],
                        scores["solution_relevance"],
                        scores["creativity"],
                        scores["feasibility"],
                        scores["presentation"],
                        comments or None,
                        total,
                        now,
                        now,
                    ),
                )
                flash("Evaluation submitted successfully.", "success")
            db.commit()
            return redirect(url_for("judge_dashboard"))

    return render_template(
        "evaluate.html",
        registration=registration,
        members=members,
        existing=existing,
        min_score=MIN_SCORE,
        max_score=MAX_SCORE,
    )


if __name__ == "__main__":
    with app.app_context():
        init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
