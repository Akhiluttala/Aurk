import hashlib
import hmac
from flask import current_app, Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from app.extensions import db, limiter, login_manager
from app.models import User
from app.security.rate_limit import LOGIN_LIMIT, REGISTER_LIMIT, PASSWORD_RESET_LIMIT
from app.security.tokens import make_token, read_token
from app.security.validators import validate_email_address, safe_text
from app.services.email import send_email

auth_bp = Blueprint("auth", __name__, template_folder="../templates")
def _safe_next_url(target):
    """
    Allow only local relative URLs.

    Prevents open-redirect attacks such as:
        //evil.example
        https://evil.example
        javascript:...
    """
    if not target:
        return None

    target = target.strip()

    if not target.startswith("/"):
        return None

    if target.startswith("//"):
        return None

    if "\\" in target:
        return None

    return target


@login_manager.user_loader
def load_user(user_id):
    try:
        user = db.session.get(User, int(user_id))
        return user if user and user.is_active else None
    except (ValueError, TypeError):
        return None

@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit(REGISTER_LIMIT)
def register():
    next_url = _safe_next_url(request.args.get("next"))
    if current_user.is_authenticated:
        return redirect(next_url or url_for("main.home"))
    if request.method == "POST":
        try:
            email = validate_email_address(request.form.get("email", ""))
            first = safe_text(request.form.get("first_name"), 100)
            last = safe_text(request.form.get("last_name"), 100)
            if not first or not last:
                raise ValueError("Enter your first and last name.")
            password = request.form.get("password", "")
            if len(password) < 12:
                raise ValueError("Password must contain at least 12 characters.")
            if User.query.filter_by(email=email).first():
                raise ValueError("Unable to create account with those details.")
            user = User(email=email, first_name=first, last_name=last, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            flash("Account created. Please sign in.", "success")
            return redirect(url_for("auth.login", next=next_url))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
    return render_template("auth/register.html", next_url=next_url)

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(LOGIN_LIMIT)
def login():
    next_url = _safe_next_url(request.args.get("next"))
    if current_user.is_authenticated:
        return redirect(next_url or url_for("main.home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()

        if (
            not user
            or not check_password_hash(user.password_hash, password)
            or not user.is_active
        ):
            # Deliberately use the same message for all failure cases.
            # This prevents account enumeration.
            flash("Invalid email or password.", "error")
        else:
            from app.services.guest_cart import merge_into_account
            merge_into_account(user)
            login_user(user, remember=False, fresh=True)

            next_url = _safe_next_url(request.args.get("next"))

            if next_url:
                return redirect(next_url)

            return redirect(url_for("main.home"))

    return render_template("auth/login.html", next_url=next_url)

@auth_bp.post("/logout")
@login_required
def logout():
    from app.admin.security import revoke_admin_session
    revoke_admin_session()
    logout_user()
    return redirect(url_for("main.home"))

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit(PASSWORD_RESET_LIMIT)
def forgot_password():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = make_token(f"{user.id}:{hashlib.sha256(user.password_hash.encode()).hexdigest()}", "password-reset")
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            try:
                send_email(
                    user.email,
                    "Reset your AURK password",
                    f"<p>Use this link to reset your password:</p><p><a href=\"{reset_url}\">Reset password</a></p>",
                )
            except Exception:
                current_app.logger.warning("Password reset email could not be sent.")
        flash("If an account exists for that email, reset instructions have been sent.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html")

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        subject = read_token(token, "password-reset", 1800)
        user_id, fingerprint = subject.split(":", 1)
        query = db.select(User).where(User.id == int(user_id))
        if request.method == "POST":
            query = query.with_for_update()
        user = db.session.execute(query.execution_options(populate_existing=True)).scalar_one_or_none()
        if user and not hmac.compare_digest(fingerprint, hashlib.sha256(user.password_hash.encode()).hexdigest()):
            user = None
    except Exception:
        user = None
    if not user:
        flash("Invalid or expired reset link.", "error")
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        password = request.form.get("password") or ""
        if len(password) < 12:
            flash("Password must contain at least 12 characters.", "error")
        else:
            user.password_hash = generate_password_hash(password)
            db.session.commit()
            flash("Password updated. Please sign in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html")
