from datetime import datetime, timezone
from app.extensions import db
from app.models.types import BigIntPrimaryKey
class Wishlist(db.Model):
    __tablename__ = "wishlists"
    id = db.Column(BigIntPrimaryKey, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    items = db.relationship("WishlistItem", back_populates="wishlist", cascade="all, delete-orphan")

class WishlistItem(db.Model):
    __tablename__ = "wishlist_items"
    id = db.Column(BigIntPrimaryKey, primary_key=True)
    wishlist_id = db.Column(db.BigInteger, db.ForeignKey("wishlists.id", ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.BigInteger, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (db.UniqueConstraint("wishlist_id", "product_id", name="uq_wishlist_product"),)
    wishlist = db.relationship("Wishlist", back_populates="items")
    product = db.relationship("Product")

class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(BigIntPrimaryKey, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    product = db.relationship("Product")
    customer = db.relationship("User")
    rating = db.Column(db.SmallInteger, nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, nullable=False, default=False, index=True)
    verified_purchase = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
