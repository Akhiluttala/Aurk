import logging
import os
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from flask import Flask, render_template, request

load_dotenv()

from app.config import (
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
)
from app.extensions import csrf, db, limiter, login_manager, migrate
from app.security.headers import apply_security_headers


def create_app(config_name=None):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    config_name = config_name or os.environ.get("FLASK_CONFIG", "development")
    configs = {"development": DevelopmentConfig, "testing": TestingConfig, "production": ProductionConfig}
    app.config.from_object(configs.get(config_name, DevelopmentConfig))

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
        "SECRET_KEY must be configured for the selected environment."
    )

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError(
        "DATABASE_URL must be configured for the selected environment."
    )

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)

   # Initialize database and migration extensions first.
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize authentication, CSRF, and rate limiting.
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"

    from app.models import register_models
    register_models()

    from app.auth.routes import auth_bp
    from app.main.routes import main_bp
    from app.products.routes import products_bp
    from app.cart.routes import cart_bp
    from app.checkout.routes import checkout_bp
    from app.orders.routes import orders_bp
    from app.admin.routes import admin_bp
    from app.api.routes import api_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main_bp)
    from app.community import community_bp
    app.register_blueprint(community_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(cart_bp, url_prefix="/cart")
    app.register_blueprint(checkout_bp, url_prefix="/checkout")
    app.register_blueprint(orders_bp, url_prefix="/account")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp)

    app.after_request(apply_security_headers)

    def error_page(error):
        code = getattr(error, "code", 500) or 500
        if code == 500:
            db.session.rollback()
        messages = {400: "Check your input and try again. If this form expired, reload the page.",
            403: "You do not have permission to access this page or perform this action.",
            404: "This page or record could not be found.", 405: "This request method is not allowed.",
            413: "This upload is too large. The total request must be 8 MB or smaller.",
            429: "Too many attempts. Please wait before trying again.",
            500: "We could not complete this request. Please try again later."}
        if request.path == "/admin" or request.path.startswith("/admin/"):
            return render_template("admin/error.html", code=code, message=messages.get(code, "Unable to complete this request.")), code
        template_code = code if code != 413 else 400
        return render_template(f"errors/{template_code}.html"), code

    for code in (400, 403, 404, 405, 413, 429, 500):
        app.register_error_handler(code, error_page)

    from app.services.order_notifications import send_order_alerts_command
    app.cli.add_command(send_order_alerts_command)
    from app.services.product_interests import send_interest_alerts_command
    app.cli.add_command(send_interest_alerts_command)

    from app.services.customer_emails import send_customer_emails_command, send_email_test_command
    app.cli.add_command(send_customer_emails_command)
    app.cli.add_command(send_email_test_command)

    configure_logging(app)
    return app


def configure_logging(app):
    if app.debug or app.testing:
        return
    handler = RotatingFileHandler("instance/ar_drips.log", maxBytes=2_000_000, backupCount=5)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
