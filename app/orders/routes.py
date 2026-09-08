from flask import Blueprint, abort, render_template, jsonify
from flask_login import current_user, login_required
from app.models import Order

orders_bp = Blueprint("orders", __name__)

@orders_bp.get("/orders")
@login_required
def list_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("account/orders.html", orders=orders)

@orders_bp.get("/orders/<order_number>")
@login_required
def detail(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first()
    if not order: abort(404)
    return render_template("account/order_detail.html", order=order)


@orders_bp.get("/orders/<order_number>/status")
@login_required
def status(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    response = jsonify(status=order.status, label=order.status_label, message=order.status_message)
    response.headers["Cache-Control"] = "no-store"
    return response
