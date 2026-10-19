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
            from app.services.customer_emails import queue_customer_email
            queue_customer_email("welcome", user)
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
        return redirect(next_url or url_for("orders.dashboard"))

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

            return redirect(url_for("orders.dashboard"))

    return render_template("auth/login.html", next_url=next_url)

@auth_bp.post("/logout")
@login_required
def logout():
    from app.admin.security import revoke_admin_session
    revoke_admin_session()
    logout_user()
    return redirect(url_for("main.home"))

def _reset_url(token):
    from urllib.parse import urlsplit
    base = current_app.config.get("PUBLIC_BASE_URL", "").rstrip("/")
    if not base and (current_app.debug or current_app.testing):
        if request.host.split(":")[0] in {"localhost", "127.0.0.1"}:
            base = request.host_url.rstrip("/")
    parsed = urlsplit(base)
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username
            or parsed.password or parsed.query or parsed.fragment
            or (not current_app.debug and not current_app.testing and parsed.scheme != "https")):
        raise RuntimeError("Configure PUBLIC_BASE_URL for password reset emails.")
    return base + url_for("auth.reset_password", token=token)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit(PASSWORD_RESET_LIMIT, methods=["POST"])
def forgot_password():
    admin_reset = request.args.get("admin") == "1"
    if request.method == "POST":
        try:
            email = validate_email_address(request.form.get("email", "").strip().lower())
        except ValueError:
            flash("Enter a valid email address.", "error")
            return render_template("auth/forgot_password.html", admin_reset=admin_reset), 400
        user = User.query.filter_by(email=email, is_active=True).first()
        if user:
            token = make_token(f"{user.id}:{hashlib.sha256(user.password_hash.encode()).hexdigest()}", "password-reset")
            try:
                from markupsafe import escape
                reset_url = _reset_url(token)
                send_email(user.email, "Reset your AURK password",
                    f'<h1>Reset your password</h1><p>Click the link below to choose a new password.</p>'
                    f'<p><a href="{escape(reset_url)}">Reset password</a></p>'
                    '<p>This link expires in 30 minutes and can only be used once. '
                    'If you did not request this, you can ignore this email.</p>',
                    f"Reset your AURK password: {reset_url}\n\nThis link expires in 30 minutes "
                    "and can only be used once. If you did not request this, ignore this email.")
            except Exception:
                current_app.logger.warning("Password reset email could not be sent. Check SMTP and PUBLIC_BASE_URL configuration.")
        return render_template("auth/forgot_password.html", admin_reset=admin_reset, sent=True)
    return render_template("auth/forgot_password.html", admin_reset=admin_reset)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def reset_password(token):
    try:
        subject = read_token(token, "password-reset", 1800)
        user_id, fingerprint = subject.split(":", 1)
        query = db.select(User).where(User.id == int(user_id))
        if request.method == "POST":
            query = query.with_for_update()
        user = db.session.execute(query.execution_options(populate_existing=True)).scalar_one_or_none()
        if user and (not user.is_active or not hmac.compare_digest(fingerprint, hashlib.sha256(user.password_hash.encode()).hexdigest())):
            user = None
    except Exception:
        db.session.rollback()
        user = None
    if not user:
        flash("This reset link is invalid, expired, or already used. Request a new email below.", "error")
        return redirect(url_for("auth.forgot_password"))
    admin_reset = user.has_role("Admin") or user.has_role("Super Admin")
    if request.method == "POST":
        password = request.form.get("password") or ""
        if not 12 <= len(password) <= 1024:
            flash("Use a password between 12 and 1024 characters.", "error")
        elif password != request.form.get("confirm_password"):
            flash("Passwords do not match. Please enter them again.", "error")
        else:
            from app.models import AdminSession
            user.password_hash = generate_password_hash(password)
            db.session.execute(db.delete(AdminSession).where(AdminSession.user_id == user.id))
            db.session.commit()
            logout_user()
            flash("Password updated. Sign in with your new password.", "success")
            return redirect(url_for("admin.login" if admin_reset else "auth.login"))
    return render_template("auth/reset_password.html", admin_reset=admin_reset)
