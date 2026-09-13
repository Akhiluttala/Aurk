from flask import Blueprint, abort, current_app, render_template, send_file
from app.models import Category, Product

main_bp = Blueprint("main", __name__)

@main_bp.app_context_processor
def brand_artwork():
    from pathlib import Path
    images = Path(current_app.static_folder) / "images" / "brand"
    return {"aurk_logo_available": (images / "logo.jpeg").is_file(),
            "aurk_hero_available": (images / "hero.png").is_file(),
            "aurk_mobile_hero_available": (images / "hero-mobile.jpg").is_file()}

@main_bp.get("/")
def home():
    featured = Product.query.filter_by(is_active=True, is_featured=True).limit(8).all()
    new_arrivals = Product.query.filter_by(is_active=True, is_new_arrival=True).order_by(Product.created_at.desc()).limit(8).all()
    bestsellers = Product.query.filter_by(is_active=True, is_bestseller=True).limit(8).all()
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order, Category.name).all()
    if not featured:
        featured = Product.query.filter_by(is_active=True).order_by(Product.created_at.desc(), Product.id.desc()).limit(8).all()
    from app.services.catalog import prepare_storefront_products
    prepare_storefront_products({p.id: p for p in featured + new_arrivals + bestsellers}.values())
    return render_template("pages/home.html", featured=featured, new_arrivals=new_arrivals, bestsellers=bestsellers, categories=categories)

@main_bp.get("/about")
def about(): return render_template("pages/about.html")
@main_bp.get("/contact")
def contact(): return render_template("pages/contact.html")
@main_bp.get("/privacy")
def privacy(): return render_template("pages/privacy.html")
@main_bp.get("/terms")
def terms(): return render_template("pages/terms.html")
@main_bp.get("/shipping")
def shipping(): return render_template("pages/shipping.html")
@main_bp.get("/returns")
def returns(): return render_template("pages/returns.html")
@main_bp.get("/refund-policy")
def refund_policy(): return render_template("pages/refund.html")


@main_bp.get("/media/<path:key>")
def media(key):
    from app.models import ProductImage
    from app.products.routes import product_image
    image = ProductImage.query.filter_by(storage_key=key).first_or_404()
    return product_image(image.id)
