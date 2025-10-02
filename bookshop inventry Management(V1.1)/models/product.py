from models import db

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=True)  # Only visible to admin
    discount = db.Column(db.Float, default=0)  # Discount amount per product
    category = db.relationship('Category', backref='products')
    __table_args__ = (db.UniqueConstraint('name', 'category_id', name='unique_name_category'),)