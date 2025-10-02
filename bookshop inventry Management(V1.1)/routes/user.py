from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.category import Category
from models.product import Product
from models.sale import Sale
from models import db
from utils.cart import get_cart, get_cart_items
from datetime import datetime

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
def home():
    query = request.args.get('q', '')
    selected_cat = request.args.get('cat_id', '')
    base = Product.query.join(Category)
    if selected_cat:
        base = base.filter(Product.category_id == int(selected_cat))
    if query:
        base = base.filter(
            (Product.name.contains(query)) | (Product.author.contains(query))
        )
    products = base.all()
    categories = Category.query.all()
    cart_items = len(get_cart())
    return render_template('home.html', products=products, query=query, categories=categories, selected_cat=selected_cat, cart_items=cart_items)

@user_bp.route('/filter_category')
def filter_category():
    cat_id = request.args.get('cat_id')
    return redirect(url_for('user.home', cat_id=cat_id))

@user_bp.route('/search')
def search():
    return redirect(url_for('user.home', q=request.args.get('q')))

@user_bp.route('/add_to_cart/<int:pid>', methods=['POST'])
def add_to_cart(pid):
    qty = int(request.form.get('qty', 1))
    product = Product.query.get_or_404(pid)
    if qty > product.quantity:
        flash('You must select less than available stock')
        return redirect(url_for('user.home'))
    cart = get_cart()
    pid_str = str(pid)
    if pid_str in cart:
        new_qty = cart[pid_str]['qty'] + qty
        if new_qty > product.quantity:
            flash('You must select less than available stock')
            return redirect(url_for('user.home'))
        cart[pid_str]['qty'] = new_qty
        # Ensure discount key exists
        if 'discount' not in cart[pid_str]:
            cart[pid_str]['discount'] = 0
    else:
        cart[pid_str] = {'qty': qty, 'discount': 0}
    session['cart'] = cart
    flash('Added to cart')
    return redirect(url_for('user.home'))

@user_bp.route('/cart')
def cart():
    items, total = get_cart_items()
    return render_template('cart.html', cart=items, total=total)

@user_bp.route('/update_cart/<int:pid>', methods=['POST'])
def update_cart(pid):
    qty = int(request.form.get('qty', 0))
    discount = float(request.form.get('discount', 0))
    product = Product.query.get_or_404(pid)
    if qty > product.quantity:
        flash('You must select less than available stock')
        return redirect(url_for('user.cart'))
    cart = get_cart()
    pid_str = str(pid)
    if qty == 0:
        if pid_str in cart:
            del cart[pid_str]
    else:
        cart[pid_str] = {'qty': qty, 'discount': discount}
    session['cart'] = cart
    flash('Cart updated')
    return redirect(url_for('user.cart'))

@user_bp.route('/remove_from_cart/<int:pid>', methods=['POST'])
def remove_from_cart(pid):
    cart = get_cart()
    pid_str = str(pid)
    if pid_str in cart:
        del cart[pid_str]
        session['cart'] = cart
    flash('Item removed from cart')
    return redirect(url_for('user.cart'))

@user_bp.route('/checkout', methods=['POST'])
def checkout():
    items, total = get_cart_items()
    if not items:
        flash('Cart is empty')
        return redirect(url_for('user.cart'))
    total_discount = sum((item.get('discount', 0) or 0) * item['qty'] for item in items)
    for item in items:
        product = Product.query.get(item['id'])
        if product.quantity < item['qty']:
            flash('You must select less than available stock for ' + product.name)
            return redirect(url_for('user.cart'))
    for item in items:
        product = Product.query.get(item['id'])
        product.quantity -= item['qty']
        sale = Sale(product_id=item['id'], quantity_sold=item['qty'], is_return=False, discount=item.get('discount', 0) or 0)
        db.session.add(sale)
    db.session.commit()
    session.pop('cart', None)
    shop_name = "Bookshop"
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    transaction_id = Sale.query.order_by(Sale.id.desc()).first().id
    return render_template('receipt.html', shop_name=shop_name, date=current_date, items=items, total=total, transaction_id=transaction_id, total_discount=total_discount)

@user_bp.route('/return', methods=['GET', 'POST'])
def returns():
    if request.method == 'POST':
        name = request.form.get('name')
        qty = int(request.form.get('qty'))
        product = Product.query.filter_by(name=name).first()
        if product:
            product.quantity += qty
            sale = Sale(product_id=product.id, quantity_sold=qty, is_return=True)
            db.session.add(sale)
            db.session.commit()
            flash('Return processed successfully', 'success')
        else:
            flash('Product not found', 'error')
        return redirect(url_for('user.returns'))
    return render_template('return.html')