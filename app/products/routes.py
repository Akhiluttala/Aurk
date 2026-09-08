from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    render_template,
    request,
    send_file,
)
from sqlalchemy import func, or_, select

from sqlalchemy.orm import selectinload
from app.services.catalog import price_bounds, prepare_storefront_products, storefront_price_expression
from app.extensions import db
from app.models import Category, Product, ProductImage, ProductVariant


products_bp = Blueprint("products", __name__)


@products_bp.get("/shop")
def shop():
    stmt = select(Product).where(Product.is_active.is_(True)).options(selectinload(Product.images), selectinload(Product.category), selectinload(Product.variants).selectinload(ProductVariant.inventory))

    q = (request.args.get("q") or "").strip()
    category_slug = (request.args.get("category") or "").strip()
    sort = request.args.get("sort", "newest")

    if q:
        like = f"%{q}%"

        stmt = stmt.where(
            or_(
                Product.name.ilike(like),
                Product.description.ilike(like),
            )
        )

    category = None
    if category_slug:
        category = (
            Category.query
            .filter_by(
                slug=category_slug,
                is_active=True
            )
            .first_or_404()
        )

        stmt = stmt.where(
            Product.category_id == category.id
        )

    if sort not in {"price_asc", "price_desc", "featured", "newest"}:
        sort = "newest"

    if sort == "price_asc":
        stmt = stmt.order_by(storefront_price_expression().asc(), Product.id.asc())

    elif sort == "price_desc":
        stmt = stmt.order_by(storefront_price_expression().desc(), Product.id.asc())

    elif sort == "featured":
        stmt = stmt.order_by(
            Product.is_featured.desc(),
            Product.created_at.desc(),
        )

    elif sort == "newest":
        stmt = stmt.order_by(
            Product.created_at.desc()
        )

    page = max(
        request.args.get("page", 1, type=int),
        1
    )

    pagination = db.paginate(
        stmt,
        page=page,
        per_page=24,
        error_out=False,
    )

    prepare_storefront_products(pagination.items)

    categories = (
        Category.query
        .filter_by(is_active=True)
        .order_by(
            Category.sort_order,
            Category.name
        )
        .all()
    )

    return render_template(
        "shop/shop.html",
        products=pagination.items,
        pagination=pagination,
        categories=categories,
        q=q,
        category_slug=category_slug,
        selected_category=category,
    )


@products_bp.get("/product/<slug>")
def detail(slug):
    product = (
        Product.query
        .filter_by(
            slug=slug,
            is_active=True
        )
        .first()
    )

    if not product:
        abort(404)

    variants = [v for v in product.variants if v.is_active]
    available_variants = [v for v in variants if v.inventory and v.inventory.quantity > v.inventory.reserved_quantity]
    low, high = price_bounds(product)
    return render_template("shop/product.html", product=product, variants=variants,
        available_variants=available_variants, min_price=low, max_price=high)


@products_bp.get("/product-image/<int:image_id>")
def product_image(image_id):
    """
    Securely serve product images.

    Only images belonging to active products are publicly
    accessible.
    """

    image = (
        ProductImage.query
        .join(Product, Product.id == ProductImage.product_id)
        .filter(
            ProductImage.id == image_id,
            Product.is_active.is_(True),
        )
        .first_or_404()
    )

    upload_dir = (
        Path(current_app.config["UPLOAD_DIR"])
        .resolve()
    )

    image_path = (
        upload_dir / image.storage_key
    ).resolve()

    # Prevent path traversal.
    try:
        image_path.relative_to(upload_dir)
    except ValueError:
        abort(404)

    if not image_path.is_file():
        abort(404)

    return send_file(
        image_path,
        mimetype=image.mime_type,
        max_age=3600,
    )


@products_bp.get("/search")
def search():
    return shop()
