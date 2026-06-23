import os
import threading
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    send_from_directory, abort, jsonify,
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user,
)

load_dotenv()

from models import db, User, Video, Setting, seed_settings, DEFAULT_SETTINGS
import video_gen

BASE_DIR = Path(__file__).parent

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR / 'instance' / 'app.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))


def admin_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*a, **kw)
    return wrap


@app.context_processor
def inject_settings():
    return {"settings": {k: Setting.get(k, v) for k, v in DEFAULT_SETTINGS.items()}}


# ---------- Public ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if not Setting.get_bool("signup_enabled", True):
        flash("Signups are currently disabled by admin.", "error")
        return redirect(url_for("login"))
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        name = request.form.get("name", "").strip()
        pwd = request.form["password"]
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return redirect(url_for("signup"))
        u = User(email=email, name=name, credits=Setting.get_int("free_credits", 5))
        u.set_password(pwd)
        db.session.add(u); db.session.commit()
        login_user(u)
        return redirect(url_for("dashboard"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pwd = request.form["password"]
        u = User.query.filter_by(email=email).first()
        if not u or not u.check_password(pwd):
            flash("Invalid credentials.", "error")
            return redirect(url_for("login"))
        if u.is_banned:
            flash("Your account has been banned.", "error")
            return redirect(url_for("login"))
        login_user(u)
        return redirect(url_for("admin_dashboard") if u.is_admin else url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# ---------- User dashboard ----------
@app.route("/dashboard")
@login_required
def dashboard():
    videos = Video.query.filter_by(user_id=current_user.id).order_by(Video.created_at.desc()).all()
    return render_template("dashboard.html", videos=videos)


@app.route("/generate", methods=["POST"])
@login_required
def generate():
    if not Setting.get_bool("video_gen_enabled", True):
        flash("Video generation is disabled by admin.", "error")
        return redirect(url_for("dashboard"))
    if current_user.credits <= 0:
        flash("No credits left. Contact admin.", "error")
        return redirect(url_for("dashboard"))
    prompt = request.form["prompt"].strip()
    max_len = Setting.get_int("max_prompt_length", 500)
    if not prompt or len(prompt) > max_len:
        flash(f"Prompt must be 1–{max_len} characters.", "error")
        return redirect(url_for("dashboard"))

    video = Video(user_id=current_user.id, prompt=prompt, status="processing")
    db.session.add(video)
    current_user.credits -= 1
    db.session.commit()

    vid_id = video.id
    def worker():
        with app.app_context():
            v = Video.query.get(vid_id)
            try:
                fname = video_gen.make_video(prompt)
                v.filename = fname
                v.status = "done"
            except Exception as e:
                v.status = "failed"
                v.error = str(e)[:500]
            db.session.commit()
    threading.Thread(target=worker, daemon=True).start()

    flash("Video generation started! Refresh in a minute.", "success")
    return redirect(url_for("dashboard"))


@app.route("/video/<int:vid>")
@login_required
def video_status(vid):
    v = Video.query.get_or_404(vid)
    if v.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    return jsonify({"status": v.status, "filename": v.filename, "error": v.error})


@app.route("/videos/<path:fname>")
@login_required
def serve_video(fname):
    return send_from_directory(BASE_DIR / "generated_videos", fname)


# ---------- Admin ----------
@app.route("/admin")
@admin_required
def admin_dashboard():
    users = User.query.order_by(User.created_at.desc()).all()
    videos = Video.query.order_by(Video.created_at.desc()).limit(50).all()
    stats = {
        "users": User.query.count(),
        "videos": Video.query.count(),
        "pending": Video.query.filter_by(status="processing").count(),
        "failed": Video.query.filter_by(status="failed").count(),
    }
    return render_template("admin/dashboard.html", users=users, videos=videos, stats=stats)


@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    if request.method == "POST":
        for key in DEFAULT_SETTINGS:
            if key in request.form:
                Setting.set(key, request.form[key])
        # checkbox booleans (unchecked = absent)
        for bkey in ("signup_enabled", "video_gen_enabled", "require_login"):
            Setting.set(bkey, "true" if request.form.get(bkey) else "false")
        flash("Settings saved.", "success")
        return redirect(url_for("admin_settings"))
    current = {k: Setting.get(k, v) for k, v in DEFAULT_SETTINGS.items()}
    return render_template("admin/settings.html", current=current)


@app.route("/admin/users/<int:uid>/<action>", methods=["POST"])
@admin_required
def admin_user_action(uid, action):
    u = User.query.get_or_404(uid)
    if u.id == current_user.id and action in ("ban", "delete"):
        flash("Cannot ban/delete yourself.", "error")
        return redirect(url_for("admin_dashboard"))
    if action == "ban":
        u.is_banned = True
    elif action == "unban":
        u.is_banned = False
    elif action == "make_admin":
        u.is_admin = True
    elif action == "remove_admin":
        u.is_admin = False
    elif action == "add_credits":
        u.credits += int(request.form.get("amount", 5))
    elif action == "delete":
        db.session.delete(u)
    db.session.commit()
    flash(f"User {u.email}: {action} done.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/videos/<int:vid>/delete", methods=["POST"])
@admin_required
def admin_delete_video(vid):
    v = Video.query.get_or_404(vid)
    if v.filename:
        try: (BASE_DIR / "generated_videos" / v.filename).unlink(missing_ok=True)
        except Exception: pass
    db.session.delete(v); db.session.commit()
    flash("Video deleted.", "success")
    return redirect(url_for("admin_dashboard"))


# ---------- Bootstrap ----------
def bootstrap():
    with app.app_context():
        db.create_all()
        seed_settings()
        admin_email = os.environ.get("ADMIN_EMAIL", "irkanmalik244255@gmail.com")
        admin_pwd = os.environ.get("ADMIN_PASSWORD", "admin@786")
        if not User.query.filter_by(email=admin_email).first():
            a = User(email=admin_email, name="Super Admin", is_admin=True, credits=9999)
            a.set_password(admin_pwd)
            db.session.add(a); db.session.commit()
            print(f"[seed] Admin created: {admin_email}")


if __name__ == "__main__":
    bootstrap()
    app.run(host="0.0.0.0", port=5000, debug=True)
