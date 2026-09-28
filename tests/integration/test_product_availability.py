from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import (Product, ProductInterest, ProductVariant, Inventory, Size, Color,
                        User, Cart, CartItem, Order, Role, Permission, Category)
from app.services import product_interests as alerts


@pytest.fixture
def catalog(app):
    with app.app_context():
        category = Category(name="Tees", slug="tees")
        product = Product(name="Launch Tee", slug="launch", base_price=999, product_status="coming_soon", category=category)
        variant = ProductVariant(product=product, size=Size(name="M"), color=Color(name="Black"), sku="LAUNCH-M")
        variant.inventory = Inventory(quantity=5, reserved_quantity=0)
        user = User(email="buyer@example.com", first_name="Buyer", last_name="Test", phone="9876543210",
                    password_hash=generate_password_hash("StrongPassword123!"))
        db.session.add_all([product, variant, user])
        db.session.commit()
        return product.id, variant.id, user.id


def login(client):
    client.post("/auth/login", data={"email": "buyer@example.com", "password": "StrongPassword123!"})


def interest(client, product_id):
    return client.post(f"/products/{product_id}/interest", headers={"Accept": "application/json"})


@pytest.mark.parametrize("status", ["coming_soon", "out_of_stock"])
def test_unavailable_visible_and_blocked(client, catalog, status):
    pid, vid, uid = catalog
    with client.application.app_context():
        db.session.get(Product, pid).product_status = status
        db.session.commit()
    for path in ("/", "/shop", "/product/launch"):
        page = client.get(path)
        assert page.status_code == 200
        assert b"availability-visual" in page.data
        assert status.replace("_", " ").upper().encode() in page.data
        assert b"I&#39;m Interested" in page.data
        assert b'action="/cart/add"' not in page.data
    client.post("/cart/add", data={"variant_id": vid})
    with client.session_transaction() as session:
        assert not session.get("guest_cart")
    login(client)
    client.post("/cart/add", data={"variant_id": vid})
    with client.application.app_context():
        assert CartItem.query.count() == 0
        cart = Cart(user_id=uid, items=[CartItem(variant_id=vid, quantity=1)])
        db.session.add(cart)
        db.session.commit()
    client.post("/checkout", data=dict(recipient_name="Buyer", phone="9876543210", line1="Street 1",
        city="Mumbai", state="Maharashtra", postal_code="400001", country="India"))
    with client.application.app_context():
        assert Order.query.count() == 0
        assert Inventory.query.one().quantity == 5


@pytest.mark.parametrize("authenticated", [True, False])
@pytest.mark.parametrize("status", ["coming_soon", "out_of_stock"])
def test_registration_duplicate_email_and_reload(client, catalog, monkeypatch, authenticated, status):
    pid, _, uid = catalog
    with client.application.app_context():
        db.session.get(Product, pid).product_status = status
        db.session.commit()
    sender = Mock()
    monkeypatch.setattr(alerts, "send_email", sender)
    client.application.config["INTEREST_NOTIFICATION_EMAIL"] = "owner@example.com"
    if authenticated:
        login(client)
    client.get("/product/launch")
    assert interest(client, pid).status_code == 200
    assert interest(client, pid).status_code == 200
    assert sender.call_count == 1
    args = sender.call_args.args
    assert args[0] == "owner@example.com"
    assert args[1] == "New Product Interest - Launch Tee"
    assert Product.STATUSES[status] in args[3]
    with client.application.app_context():
        row = ProductInterest.query.one()
        assert row.customer_id == (uid if authenticated else None)
        assert row.customer_email == ("buyer@example.com" if authenticated else None)
        assert row.notified_at
    assert b"Interest Registered" in client.get("/product/launch").data


def test_email_failure_saved_and_retryable(client, catalog, monkeypatch):
    pid, _, _ = catalog
    sender = Mock(side_effect=RuntimeError("SMTP down"))
    monkeypatch.setattr(alerts, "send_email", sender)
    client.get("/shop")
    assert interest(client, pid).status_code == 200
    with client.application.app_context():
        assert ProductInterest.query.one().notified_at is None
    sender.side_effect = None
    result = client.application.test_cli_runner().invoke(args=["send-interest-alerts"])
    assert result.exit_code == 0
    assert "Sent 1" in result.output
    client.application.test_cli_runner().invoke(args=["send-interest-alerts"])
    assert sender.call_count == 2


def test_status_transition_and_invalid_product(client, catalog, monkeypatch):
    pid, vid, _ = catalog
    monkeypatch.setattr(alerts, "send_email", Mock())
    client.get("/shop")
    assert interest(client, 99999).status_code == 404
    assert interest(client, pid).status_code == 200
    with client.application.app_context():
        db.session.get(Product, pid).product_status = "available"
        db.session.commit()
    page = client.get("/product/launch")
    assert b"data-interest-form" not in page.data
    assert b'action="/cart/add"' in page.data
    assert interest(client, pid).status_code == 409
    client.post("/cart/add", data={"variant_id": vid})
    with client.session_transaction() as session:
        assert session["guest_cart"][str(vid)] == 1


def test_database_failure_allows_retry(client, catalog, monkeypatch):
    client.get("/shop")
    original = db.session.commit
    monkeypatch.setattr(db.session, "commit", Mock(side_effect=SQLAlchemyError("database failed")))
    assert interest(client, catalog[0]).status_code == 503
    monkeypatch.setattr(db.session, "commit", original)
    monkeypatch.setattr(alerts, "send_email", Mock())
    assert interest(client, catalog[0]).status_code == 200
    with client.application.app_context():
        assert ProductInterest.query.count() == 1


def test_csrf_and_product_deletion(client, catalog, monkeypatch):
    pid, _, _ = catalog
    client.application.config["WTF_CSRF_ENABLED"] = True
    assert interest(client, pid).status_code == 400
    client.application.config["WTF_CSRF_ENABLED"] = False
    monkeypatch.setattr(alerts, "send_email", Mock())
    client.get("/shop")
    interest(client, pid)
    with client.application.app_context():
        db.session.delete(db.session.get(Product, pid))
        db.session.commit()
        assert ProductInterest.query.count() == 0


def test_admin_status_and_interest_permissions(client, catalog):
    pid, _, uid = catalog
    assert client.get("/admin/interests").status_code == 302
    login(client)
    assert client.get("/admin/interests").status_code == 403
    client.post("/auth/logout")
    with client.application.app_context():
        user = db.session.get(User, uid)
        user.roles.append(Role(name="Admin", permissions=[Permission(name="products.update"), Permission(name="customers.manage")]))
        db.session.commit()
    client.post("/admin/login", data={"email": "buyer@example.com", "password": "StrongPassword123!"})
    assert client.get("/admin/interests").status_code == 200
    with client.application.app_context():
        category_id = db.session.get(Product, pid).category_id
    form = dict(name="Launch Tee", slug="launch", base_price="999", category_id=category_id, is_active="1")
    for status in ("out_of_stock", "available", "coming_soon"):
        assert client.post(f"/admin/products/{pid}/edit", data={**form, "product_status": status}).status_code == 302
        with client.application.app_context():
            assert db.session.get(Product, pid).product_status == status
    assert client.post(f"/admin/products/{pid}/edit", data={**form, "product_status": "invalid"}).status_code == 400
