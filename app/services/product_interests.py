"""Persist interest before SMTP delivery; failed notifications remain retryable."""
from datetime import datetime, timezone
from html import escape

import click
from flask import current_app
from flask.cli import with_appcontext

from app.extensions import db
from app.models import Product, ProductInterest
from app.services.email import send_email


def notify_interest(interest_id):
    try:
        interest = db.session.scalar(db.select(ProductInterest).where(ProductInterest.id == interest_id)
            .with_for_update().execution_options(populate_existing=True))
        if not interest or interest.notified_at:
            db.session.rollback()
            return True
        body = "\n\n".join([
            "Product Interest Notification", f"Product:\n{interest.product.name}",
            f"Product ID:\n{interest.product_id}", f"Status:\n{Product.STATUSES[interest.product_status]}",
            f"Customer:\n{interest.customer_name or 'Guest'}",
            f"Customer Email:\n{interest.customer_email or 'Not provided'}",
            f"Customer Phone:\n{interest.customer_phone or 'Not provided'}",
            f"Time:\n{interest.created_at:%Y-%m-%d %H:%M:%S} UTC",
        ])
        name = " ".join(interest.product.name.splitlines())
        support = current_app.config["CUSTOMER_SUPPORT_EMAIL"]
        send_email(current_app.config.get("INTEREST_NOTIFICATION_EMAIL") or support,
            f"New Product Interest - {name}", f"<pre>{escape(body)}</pre>", body,
            from_email=support, reply_to=interest.customer_email or support)
        interest.notified_at = datetime.now(timezone.utc)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        current_app.logger.warning("Product interest %s saved; notification pending retry.", interest_id)
        return False


@click.command("send-interest-alerts")
@with_appcontext
def send_interest_alerts_command():
    """Retry up to 100 pending product interest emails (schedule periodically)."""
    ids = list(db.session.scalars(db.select(ProductInterest.id)
        .where(ProductInterest.notified_at.is_(None)).order_by(ProductInterest.id).limit(100)))
    db.session.rollback()
    sent = sum(notify_interest(interest_id) for interest_id in ids)
    click.echo(f"Sent {sent}; pending {len(ids) - sent} in this batch.")
