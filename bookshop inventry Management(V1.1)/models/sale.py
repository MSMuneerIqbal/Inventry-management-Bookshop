from models import db
from datetime import datetime

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity_sold = db.Column(db.Integer, nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_return = db.Column(db.Boolean, default=False)
    discount = db.Column(db.Float, default=0)  # Discount per unit at time of sale
    product = db.relationship('Product', backref='sales')

    def __repr__(self):
        return f"Sale(id={self.id}, product_id={self.product_id}, quantity_sold={self.quantity_sold}, sale_date='{self.sale_date}', is_return={self.is_return})"