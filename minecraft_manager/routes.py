import sqlite3
import secrets
from functools import wraps

from flask import (
    abort,
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .minecraft import (
    add_to_whitelist,
    latest_backups,
    load_whitelist,
    make_backup,
    remove_from_whitelist,
    run_admin_command,
    status,
    validate_minecraft_name,
)


bp = Blueprint("main", __name__)


@bp.before_app_request
def validate_csrf():
    if request.method != "POST":
        return
    token = session.get("csrf_token")
    form_token = request.form.get("csrf_token")
    if not token or not form_token or not secrets.compare_digest(token, form_token):
        abort(400)


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.get_user(user_id)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Log in to continue.", "warning")
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            flash("Log in to continue.", "warning")
            return redirect(url_for("main.login"))
        if not user["is_admin"]:
            flash("Admin access is required.", "error")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)

    return wrapped


@bp.app_context_processor
def inject_user():
    return {"current_user": current_user(), "csrf_token": csrf_token}


@bp.route("/")
def index():
    if current_user():
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))


@bp.route("/register", methods=("GET", "POST"))
def register():
    first_user = db.user_count() == 0
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        minecraft_name = request.form.get("minecraft_name", "").strip()

        if not email or "@" not in email:
            flash("Enter a valid email address.", "error")
        elif len(password) < 10:
            flash("Use a password with at least 10 characters.", "error")
        elif not validate_minecraft_name(minecraft_name):
            flash("Minecraft usernames must be 3-16 characters: letters, numbers, and underscores.", "error")
        else:
            try:
                user_id = db.create_user(
                    email=email,
                    password_hash=generate_password_hash(password),
                    minecraft_name=minecraft_name,
                    is_admin=first_user,
                )
                whitelist_message = None
                if current_app.config["AUTO_WHITELIST_ON_REGISTER"]:
                    whitelist_result = add_to_whitelist(minecraft_name)
                    if not whitelist_result.ok:
                        whitelist_message = whitelist_result.message
                session.clear()
                session["user_id"] = user_id
                if whitelist_message:
                    flash(whitelist_message, "warning")
                flash("Account created.", "success")
                return redirect(url_for("main.dashboard"))
            except sqlite3.IntegrityError:
                flash("That email or Minecraft username is already registered.", "error")

    return render_template("register.html", first_user=first_user)


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = db.get_user_by_email(email)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("main.dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("main.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", server=status())


@bp.route("/admin")
@admin_required
def admin():
    return render_template(
        "admin.html",
        server=status(),
        users=db.list_users(),
        whitelist=load_whitelist(),
        backups=latest_backups(),
    )


@bp.route("/admin/action/<action>", methods=("POST",))
@admin_required
def server_action(action: str):
    if action == "backup":
        result = make_backup()
    elif action == "backup_restart":
        backup = make_backup()
        if backup.ok:
            restart = run_admin_command("restart")
            result = restart if not restart.ok else backup
        else:
            result = backup
    elif action in {"start", "stop", "restart"}:
        result = run_admin_command(action)
    elif action == "upgrade":
        stop = run_admin_command("stop")
        if not stop.ok:
            result = stop
        else:
            backup = make_backup()
            if not backup.ok:
                result = backup
            else:
                upgrade = run_admin_command("upgrade")
                if not upgrade.ok:
                    result = upgrade
                else:
                    result = run_admin_command("start")
                    if result.ok:
                        result.message = "Upgrade command completed, backup created, and server started."
    else:
        result = type("Result", (), {"ok": False, "message": "Unknown action."})()

    flash(result.message, "success" if result.ok else "error")
    return redirect(url_for("main.admin"))


@bp.route("/admin/users/<int:user_id>/admin", methods=("POST",))
@admin_required
def toggle_admin(user_id: int):
    user = db.get_user(user_id)
    if not user:
        flash("User not found.", "error")
    elif user["id"] == current_user()["id"]:
        flash("You cannot remove your own admin access.", "error")
    else:
        db.set_admin(user_id, not bool(user["is_admin"]))
        flash("Admin access updated.", "success")
    return redirect(url_for("main.admin"))


@bp.route("/admin/whitelist", methods=("POST",))
@admin_required
def whitelist_add():
    username = request.form.get("minecraft_name", "").strip()
    result = add_to_whitelist(username)
    flash(result.message, "success" if result.ok else "error")
    return redirect(url_for("main.admin"))


@bp.route("/admin/whitelist/<name>/remove", methods=("POST",))
@admin_required
def whitelist_remove(name: str):
    result = remove_from_whitelist(name)
    flash(result.message, "success" if result.ok else "error")
    return redirect(url_for("main.admin"))
