from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from models import db
from routes.user import user_bp
from routes.admin import admin_bp

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Register Blueprints
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')

# Import models within app context to avoid circular imports
with app.app_context():
    from models.category import Category
    from models.product import Product
    from models.sale import Sale
    db.create_all()
    if Category.query.count() == 0:
        default_cat = Category(name='General')
        db.session.add(default_cat)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)