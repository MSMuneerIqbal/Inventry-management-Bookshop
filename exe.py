"""
BABA BANGLES POS - Single-file desktop application
Run:   python run.py
EXE:   pyinstaller --onedir --windowed --icon=bookshop.ico
       --add-data="templates;templates" --add-data="static;static"
       --name=BabaBangles exe.py
"""

import sys, os, threading, time, io, json, sqlite3
from datetime import datetime, date, timedelta

if getattr(sys, 'frozen', False):
    _BASE = sys._MEIPASS
    os.environ.setdefault('BOOKSHOP_DB_DIR', os.path.dirname(sys.executable))
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))

from flask import (Flask, render_template, request, redirect,
                   session, flash, send_file)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, case, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import joinedload
import pandas as pd

if getattr(sys, 'frozen', False):
    app = Flask(__name__,
                template_folder=os.path.join(_BASE, 'templates'),
                static_folder=os.path.join(_BASE, 'static'))
else:
    app = Flask(__name__)

_db_dir  = os.environ.get('BOOKSHOP_DB_DIR', '')
_db_path = os.path.join(_db_dir, 'database.db') if _db_dir else None
app.config['SECRET_KEY']                     = 'baba-bangles-key-2024'
app.config['SQLALCHEMY_DATABASE_URI']        = f'sqlite:///{_db_path}' if _db_path else 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS']      = {
    'pool_pre_ping': True,
    'connect_args': {'check_same_thread': False},
}
db = SQLAlchemy(app)

PER_PAGE = 50  # rows per page on all paginated list views


# ── SQLite performance pragmas (applied on every new connection) ─────────────
@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _rec):
    if not isinstance(dbapi_conn, sqlite3.Connection):
        return
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")       # concurrent reads during write
    cur.execute("PRAGMA synchronous=NORMAL")      # safe but faster than FULL
    cur.execute("PRAGMA cache_size=-65536")       # 64 MB page cache
    cur.execute("PRAGMA temp_store=MEMORY")       # temp tables in RAM
    cur.execute("PRAGMA mmap_size=268435456")     # 256 MB memory-mapped I/O
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


# ══════════════════════════════════════════════════════════════════════════════
#  MODELS  (index=True on all columns used in WHERE / JOIN / ORDER BY)
# ══════════════════════════════════════════════════════════════════════════════

class Category(db.Model):
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)


class Product(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(100), nullable=False, index=True)
    description     = db.Column(db.Text, default='')
    category_id     = db.Column(db.Integer, db.ForeignKey('category.id'),
                                nullable=False, index=True)
    quantity        = db.Column(db.Integer, default=0, index=True)
    price           = db.Column(db.Float, nullable=False)
    purchase_price  = db.Column(db.Float, nullable=True)
    discount        = db.Column(db.Float, default=0)
    low_stock_limit = db.Column(db.Integer, default=5)
    category        = db.relationship('Category', backref='products')
    __table_args__  = (
        db.UniqueConstraint('name', 'category_id', name='unique_name_category'),
    )


class Sale(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    product_id    = db.Column(db.Integer, db.ForeignKey('product.id'),
                              nullable=False, index=True)
    quantity_sold = db.Column(db.Integer, nullable=False)
    sale_date     = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_return     = db.Column(db.Boolean, default=False, index=True)
    discount      = db.Column(db.Float, default=0)
    product       = db.relationship('Product', backref='sales')


class StockIn(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    product_id     = db.Column(db.Integer, db.ForeignKey('product.id'),
                               nullable=False, index=True)
    quantity_added = db.Column(db.Integer, nullable=False)
    date_added     = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    note           = db.Column(db.String(200), default='')
    product        = db.relationship('Product', backref='stock_ins')


class ShopSettings(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    shop_name      = db.Column(db.String(200), default='Bookshop')
    address        = db.Column(db.String(300), default='')
    contact1_name  = db.Column(db.String(100), default='')
    contact1_phone = db.Column(db.String(50),  default='')
    contact2_name  = db.Column(db.String(100), default='')
    contact2_phone = db.Column(db.String(50),  default='')
    bill_note      = db.Column(db.Text,         default='')
    color_scheme   = db.Column(db.String(20),   default='blue')


# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE INIT + MIGRATIONS
# ══════════════════════════════════════════════════════════════════════════════

def _migrate(sql):
    with db.engine.connect() as c:
        try: c.execute(text(sql)); c.commit()
        except Exception: pass

with app.app_context():
    db.create_all()
    # Column migrations (idempotent – SQLite ignores duplicate column errors)
    _migrate('ALTER TABLE shop_settings ADD COLUMN address VARCHAR(300) DEFAULT ""')
    _migrate('ALTER TABLE shop_settings ADD COLUMN color_scheme VARCHAR(20) DEFAULT "blue"')
    _migrate('ALTER TABLE product ADD COLUMN description TEXT DEFAULT ""')
    _migrate('ALTER TABLE product ADD COLUMN low_stock_limit INTEGER DEFAULT 5')

    # Explicit indexes (SQLAlchemy may not create these for existing DBs)
    _migrate('CREATE INDEX IF NOT EXISTS ix_sale_sale_date   ON sale(sale_date)')
    _migrate('CREATE INDEX IF NOT EXISTS ix_sale_product_id  ON sale(product_id)')
    _migrate('CREATE INDEX IF NOT EXISTS ix_sale_is_return   ON sale(is_return)')
    _migrate('CREATE INDEX IF NOT EXISTS ix_product_category ON product(category_id)')
    _migrate('CREATE INDEX IF NOT EXISTS ix_product_qty      ON product(quantity)')
    _migrate('CREATE INDEX IF NOT EXISTS ix_stockin_date     ON stock_in(date_added)')
    _migrate('CREATE INDEX IF NOT EXISTS ix_stockin_product  ON stock_in(product_id)')
    # Composite index: the most common query on Sale
    _migrate('CREATE INDEX IF NOT EXISTS ix_sale_date_return ON sale(sale_date, is_return)')

    if Category.query.count() == 0:
        db.session.add(Category(name='General')); db.session.commit()

    if ShopSettings.query.count() == 0:
        db.session.add(ShopSettings(
            shop_name='BABA BANGLES AND GENERAL STORE',
            address='Madina Bazar Dunyapur',
            bill_note='Thank you! Please visit again.',
            color_scheme='blue',
        )); db.session.commit()
    else:
        _s = ShopSettings.query.first()
        if _s and _s.shop_name and '\u0645\u06a9\u062a\u0628' in _s.shop_name:
            _s.shop_name = 'BABA BANGLES AND GENERAL STORE'
            _s.address   = 'Madina Bazar Dunyapur'
            db.session.commit()


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

@app.context_processor
def inject_globals():
    s = ShopSettings.query.first()
    return {'shop_settings': s, 'color_scheme': s.color_scheme if s else 'blue'}


def get_cart():
    if 'cart' not in session: session['cart'] = {}
    return session['cart']


def get_cart_items():
    cart, items, total = get_cart(), [], 0
    for pid, data in cart.items():
        p = db.session.get(Product, int(pid))
        if p:
            disc = data.get('discount', p.discount)
            pad  = max(p.price - disc, 0)
            total += pad * data['qty']
            items.append({'id': int(pid), 'name': p.name, 'qty': data['qty'],
                          'price': p.price, 'discount': disc,
                          'price_after_discount': pad, 'max_qty': p.quantity})
    return items, total


def admin_required():
    if 'admin_logged_in' not in session:
        return redirect('/admin/login')


def _parse_dates(start_key='start_date', end_key='end_date'):
    """Parse start/end dates from GET args. Returns (start_dt, end_dt, start_str, end_str) or Nones."""
    s = request.args.get(start_key, '')
    e = request.args.get(end_key, '')
    try:
        start = datetime.strptime(s, '%Y-%m-%d')
        end   = datetime.strptime(e, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        if start > end: return None, None, s, e
        return start, end, s, e
    except Exception:
        return None, None, s, e


def _sale_stats_sql(start, end):
    """Return (revenue, profit, qty_sold) using a single SQL query — zero Python loops."""
    row = db.session.query(
        func.coalesce(func.sum(case(
            (Sale.is_return == False,
             (Product.price - func.coalesce(Sale.discount, 0.0)) * Sale.quantity_sold),
            else_=0.0
        )), 0.0),
        func.coalesce(func.sum(case(
            (Sale.is_return == False,
             (Product.price - func.coalesce(Sale.discount, 0.0)
              - func.coalesce(Product.purchase_price, 0.0)) * Sale.quantity_sold),
            else_=0.0
        )), 0.0),
        func.coalesce(func.sum(case(
            (Sale.is_return == False, Sale.quantity_sold), else_=0
        )), 0),
    ).join(Product, Sale.product_id == Product.id).filter(
        Sale.sale_date >= start, Sale.sale_date <= end
    ).first()
    return float(row[0]), float(row[1]), int(row[2])


def _paginate(query, page):
    """Return (items, total_pages, total_count) for a given page."""
    total = query.count()
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page  = max(1, min(page, pages))
    items = query.limit(PER_PAGE).offset((page - 1) * PER_PAGE).all()
    return items, pages, total, page


# ══════════════════════════════════════════════════════════════════════════════
#  USER / POS ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def home():
    query        = request.args.get('q', '')
    selected_cat = request.args.get('cat_id', '')
    base = Product.query.join(Category)
    if selected_cat:
        base = base.filter(Product.category_id == int(selected_cat))
    if query:
        base = base.filter(
            (Product.name.contains(query)) | (Product.description.contains(query))
        )
    products   = base.order_by(Product.name).all()
    categories = Category.query.order_by(Category.name).all()
    cart_items = len(get_cart())
    return render_template('home.html', products=products, query=query,
                           categories=categories, selected_cat=selected_cat,
                           cart_items=cart_items)


@app.route('/search')
def search():
    return redirect(f"/?q={request.args.get('q','')}")


@app.route('/add_to_cart/<int:pid>', methods=['POST'])
def add_to_cart(pid):
    qty = int(request.form.get('qty', 1))
    p   = Product.query.get_or_404(pid)
    if qty > p.quantity:
        flash('Quantity exceeds available stock'); return redirect('/')
    cart = get_cart(); pid_str = str(pid)
    if pid_str in cart:
        nq = cart[pid_str]['qty'] + qty
        if nq > p.quantity:
            flash('Quantity exceeds available stock'); return redirect('/')
        cart[pid_str]['qty'] = nq
        cart[pid_str].setdefault('discount', 0)
    else:
        cart[pid_str] = {'qty': qty, 'discount': 0}
    session['cart'] = cart
    flash('Added to cart')
    return redirect('/')


@app.route('/cart')
def cart():
    items, total = get_cart_items()
    return render_template('cart.html', cart=items, total=total)


@app.route('/update_cart/<int:pid>', methods=['POST'])
def update_cart(pid):
    qty  = int(request.form.get('qty', 0))
    disc = float(request.form.get('discount', 0))
    p    = Product.query.get_or_404(pid)
    if qty > p.quantity:
        flash('Quantity exceeds available stock'); return redirect('/cart')
    cart = get_cart(); pid_str = str(pid)
    if qty == 0: cart.pop(pid_str, None)
    else:        cart[pid_str] = {'qty': qty, 'discount': disc}
    session['cart'] = cart
    flash('Cart updated'); return redirect('/cart')


@app.route('/remove_from_cart/<int:pid>', methods=['POST'])
def remove_from_cart(pid):
    cart = get_cart(); cart.pop(str(pid), None)
    session['cart'] = cart; flash('Item removed'); return redirect('/cart')


@app.route('/checkout', methods=['POST'])
def checkout():
    items, total = get_cart_items()
    if not items: flash('Cart is empty'); return redirect('/cart')
    total_discount = sum((i.get('discount', 0) or 0) * i['qty'] for i in items)
    for i in items:
        p = db.session.get(Product, i['id'])
        if p.quantity < i['qty']:
            flash(f'Insufficient stock for {p.name}'); return redirect('/cart')
    for i in items:
        p = db.session.get(Product, i['id'])
        p.quantity -= i['qty']
        db.session.add(Sale(product_id=i['id'], quantity_sold=i['qty'],
                            is_return=False, discount=i.get('discount', 0) or 0))
    db.session.commit()
    session.pop('cart', None)
    tid = Sale.query.order_by(Sale.id.desc()).first().id
    return render_template('receipt.html',
                           date=datetime.now().strftime('%d-%m-%Y %H:%M'),
                           items=items, total=total, transaction_id=tid,
                           total_discount=total_discount)


@app.route('/return', methods=['GET', 'POST'])
def returns():
    if request.method == 'POST':
        name = request.form.get('name'); qty = int(request.form.get('qty'))
        p    = Product.query.filter_by(name=name).first()
        if p:
            p.quantity += qty
            db.session.add(Sale(product_id=p.id, quantity_sold=qty, is_return=True))
            db.session.commit(); flash('Return processed successfully', 'success')
        else:
            flash('Product not found', 'error')
        return redirect('/return')
    return render_template('return.html')


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/admin/', methods=['GET', 'POST'])
@app.route('/admin',  methods=['GET', 'POST'])
def admin_dashboard():
    guard = admin_required()
    if guard: return guard

    today_d   = date.today()
    today_str = today_d.isoformat()
    period    = request.form.get('period', 'today')

    if period == 'today':
        start_str = end_str = today_str
    elif period == 'week':
        week_start = today_d - timedelta(days=today_d.weekday())
        start_str  = week_start.isoformat()
        end_str    = today_str
    elif period == 'month':
        start_str = today_d.replace(day=1).isoformat()
        end_str   = today_str
    else:
        start_str = request.form.get('start_date', today_str)
        end_str   = request.form.get('end_date',   today_str)

    try:
        start = datetime.strptime(start_str, '%Y-%m-%d')
        end   = datetime.strptime(end_str,   '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    except Exception:
        start = end = datetime.utcnow()

    # ── Aggregated stats via SQL (zero Python loops) ──────────────────────────
    revenue, profit, qty_sold = _sale_stats_sql(start, end)

    # ── Hot items — single GROUP BY query, top 10 ────────────────────────────
    hot_raw = (
        db.session.query(Sale.product_id,
                         func.sum(Sale.quantity_sold).label('total'))
        .filter(Sale.sale_date >= start, Sale.sale_date <= end,
                Sale.is_return == False)
        .group_by(Sale.product_id)
        .order_by(func.sum(Sale.quantity_sold).desc())
        .limit(10).all()
    )
    pids = [r.product_id for r in hot_raw]
    prod_map = {p.id: p for p in Product.query.filter(Product.id.in_(pids))
                                              .options(joinedload(Product.category)).all()} if pids else {}
    hot_items = [{'product': prod_map[r.product_id], 'qty': int(r.total)}
                 for r in hot_raw if r.product_id in prod_map]

    # ── Overview stats — all via SQL aggregation ──────────────────────────────
    total_products  = db.session.query(func.count(Product.id)).scalar()
    total_cats      = db.session.query(func.count(Category.id)).scalar()
    low_stock_count = db.session.query(func.count(Product.id)).filter(
        Product.quantity < Product.low_stock_limit).scalar()
    out_of_stock    = db.session.query(func.count(Product.id)).filter(
        Product.quantity == 0).scalar()
    total_stock_val = db.session.query(
        func.coalesce(func.sum(
            func.coalesce(Product.purchase_price, Product.price) * Product.quantity
        ), 0)
    ).scalar() or 0

    # ── Category stock bars — single GROUP BY ─────────────────────────────────
    cat_rows = (
        db.session.query(
            Category.name,
            func.count(Product.id).label('cnt'),
            func.coalesce(func.sum(case(
                (Product.quantity < Product.low_stock_limit, 1), else_=0
            )), 0).label('low')
        )
        .outerjoin(Product, Category.id == Product.category_id)
        .group_by(Category.id)
        .order_by(func.count(Product.id).desc())
        .all()
    )
    cat_stats = [{'name': r.name, 'count': r.cnt or 0, 'low': r.low or 0} for r in cat_rows]
    max_count = max((c['count'] for c in cat_stats), default=1) or 1

    return render_template('admin/dashboard.html',
        start_str=start_str, end_str=end_str, active_period=period,
        revenue=revenue, profit=profit, qty_sold=qty_sold,
        hot_items=hot_items,
        total_products=total_products, total_cats=total_cats,
        low_stock_count=low_stock_count, out_of_stock=out_of_stock,
        total_stock_val=total_stock_val,
        cat_stats=cat_stats, max_count=max_count,
    )


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['password'] == 'admin@321':
            session['admin_logged_in'] = True
            return redirect('/admin/')
        flash('Invalid password')
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None); return redirect('/')


# ── Products ──────────────────────────────────────────────────────────────────

@app.route('/admin/products')
def admin_products():
    guard = admin_required()
    if guard: return guard
    q    = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    base = Product.query.options(joinedload(Product.category)).join(Category)
    if q:
        base = base.filter(Product.name.contains(q) | Product.description.contains(q))
    base = base.order_by(Product.name)
    products, total_pages, total_count, page = _paginate(base, page)
    return render_template('admin/products.html',
        products=products, q=q, page=page,
        total_pages=total_pages, total_count=total_count)


@app.route('/admin/add', methods=['GET', 'POST'])
def admin_add():
    guard = admin_required()
    if guard: return guard
    categories = Category.query.order_by(Category.name).all()
    if request.method == 'POST':
        name            = request.form['name']
        description     = request.form.get('description', '')
        category_id     = int(request.form['category_id'])
        quantity        = int(request.form['quantity'])
        price           = float(request.form['price'])
        purchase_price  = request.form.get('purchase_price')
        purchase_price  = float(purchase_price) if purchase_price else None
        low_stock_limit = int(request.form.get('low_stock_limit') or 5)
        if Product.query.filter_by(name=name, category_id=category_id).first():
            flash('Product with this name already exists in this category')
            return redirect('/admin/add')
        try:
            p = Product(name=name, description=description,
                        category_id=category_id, quantity=quantity,
                        price=price, purchase_price=purchase_price,
                        low_stock_limit=low_stock_limit)
            db.session.add(p)
            db.session.flush()
            if quantity > 0:
                db.session.add(StockIn(product_id=p.id,
                                       quantity_added=quantity,
                                       note='Initial stock'))
            db.session.commit(); flash('Product added')
            return redirect('/admin/products')
        except Exception:
            db.session.rollback()
            flash('Could not save product'); return redirect('/admin/add')
    return render_template('admin/add.html', categories=categories)


@app.route('/admin/update/<int:pid>', methods=['GET', 'POST'])
def admin_update(pid):
    guard = admin_required()
    if guard: return guard
    product = Product.query.get_or_404(pid)
    categories = Category.query.order_by(Category.name).all()
    if request.method == 'POST':
        name            = request.form['name']
        description     = request.form.get('description', '')
        category_id     = int(request.form['category_id'])
        quantity        = int(request.form['quantity'])
        price           = float(request.form['price'])
        purchase_price  = request.form.get('purchase_price')
        low_stock_limit = int(request.form.get('low_stock_limit') or 5)
        if name != product.name or category_id != product.category_id:
            ex = Product.query.filter_by(name=name, category_id=category_id).first()
            if ex and ex.id != pid:
                flash('Name already exists in this category')
                return redirect(f'/admin/update/{pid}')
        old_qty = product.quantity
        product.name            = name
        product.description     = description
        product.category_id     = category_id
        product.quantity        = quantity
        product.price           = price
        product.purchase_price  = float(purchase_price) if purchase_price else None
        product.low_stock_limit = low_stock_limit
        if quantity > old_qty:
            db.session.add(StockIn(product_id=pid,
                                   quantity_added=quantity - old_qty,
                                   note='Admin restock'))
        try:
            db.session.commit(); flash('Product updated')
            return redirect('/admin/products')
        except Exception:
            db.session.rollback(); flash('Update failed')
            return redirect(f'/admin/update/{pid}')
    return render_template('admin/update.html', product=product, categories=categories)


@app.route('/admin/delete/<int:pid>', methods=['POST'])
def admin_delete(pid):
    guard = admin_required()
    if guard: return guard
    p = db.session.get(Product, pid)
    if p is None:
        flash('Product not found'); return redirect('/admin/products')
    sale_count = db.session.query(func.count(Sale.id)).filter_by(product_id=pid).scalar()
    if sale_count:
        flash(f'Cannot delete "{p.name}": it has {sale_count} sale record(s). Set quantity to 0 instead.')
        return redirect('/admin/products')
    StockIn.query.filter_by(product_id=pid).delete()
    db.session.delete(p)
    db.session.commit()
    flash('Product deleted')
    return redirect('/admin/products')


# ── Categories ────────────────────────────────────────────────────────────────

@app.route('/admin/categories')
def admin_categories():
    guard = admin_required()
    if guard: return guard
    return render_template('admin/categories.html',
        categories=Category.query.order_by(Category.name).all())


@app.route('/admin/add_category', methods=['GET', 'POST'])
def admin_add_category():
    guard = admin_required()
    if guard: return guard
    if request.method == 'POST':
        db.session.add(Category(name=request.form['name']))
        db.session.commit(); flash('Category added')
        return redirect('/admin/categories')
    return render_template('admin/add_category.html')


@app.route('/admin/update_category/<int:cid>', methods=['GET', 'POST'])
def admin_update_category(cid):
    guard = admin_required()
    if guard: return guard
    cat = Category.query.get_or_404(cid)
    if request.method == 'POST':
        cat.name = request.form['name']
        db.session.commit(); flash('Category updated')
        return redirect('/admin/categories')
    return render_template('admin/update_category.html', category=cat)


@app.route('/admin/delete_category/<int:cid>', methods=['POST'])
def admin_delete_category(cid):
    guard = admin_required()
    if guard: return guard
    cat = Category.query.get_or_404(cid)
    if Product.query.filter_by(category_id=cid).count() == 0:
        db.session.delete(cat); db.session.commit(); flash('Category deleted')
    else:
        flash('Cannot delete: category has products')
    return redirect('/admin/categories')


# ── Sales Report  (GET — date params in URL, supports pagination) ─────────────

@app.route('/admin/sales')
def admin_sales():
    guard = admin_required()
    if guard: return guard

    start, end, start_str, end_str = _parse_dates()
    page = request.args.get('page', 1, type=int)
    sales = []; revenue = profit = qty_sold = 0
    daily_labels = daily_values = '[]'
    total_pages = 1; total_count = 0

    if start and end:
        # Stats — single SQL query
        revenue, profit, qty_sold = _sale_stats_sql(start, end)

        # Chart — GROUP BY date, pure SQL
        daily_raw = (
            db.session.query(
                func.date(Sale.sale_date).label('day'),
                func.sum((Product.price - func.coalesce(Sale.discount, 0.0))
                         * Sale.quantity_sold).label('rev')
            ).join(Product).filter(
                Sale.sale_date >= start, Sale.sale_date <= end,
                Sale.is_return == False
            ).group_by(func.date(Sale.sale_date))
             .order_by(func.date(Sale.sale_date)).all()
        )
        daily_labels = json.dumps([r.day for r in daily_raw])
        daily_values = json.dumps([round(float(r.rev or 0), 2) for r in daily_raw])

        # Paginated table with eager join (no N+1)
        sale_q = (
            Sale.query
            .options(joinedload(Sale.product).joinedload(Product.category))
            .filter(Sale.sale_date >= start, Sale.sale_date <= end)
            .order_by(Sale.sale_date.desc())
        )
        sales, total_pages, total_count, page = _paginate(sale_q, page)
        if not sales and page == 1:
            flash('No sales in selected date range')
    elif start_str or end_str:
        flash('Invalid or missing dates')

    return render_template('admin/sales.html',
        sales=sales, start_str=start_str, end_str=end_str,
        revenue=revenue, profit=profit, qty_sold=qty_sold,
        daily_labels=daily_labels, daily_values=daily_values,
        page=page, total_pages=total_pages, total_count=total_count)


@app.route('/admin/sales/export')
def admin_sales_export():
    guard = admin_required()
    if guard: return guard
    start, end, start_str, end_str = _parse_dates()
    if not start:
        flash('Invalid date'); return redirect('/admin/sales')

    sql = text("""
        SELECT
            strftime('%Y-%m-%d %H:%M', s.sale_date) AS "Date",
            p.name   AS "Product",
            c.name   AS "Category",
            s.quantity_sold AS "Quantity",
            p.price  AS "Price",
            COALESCE(s.discount,0) AS "Discount",
            p.price - COALESCE(s.discount,0) AS "Sale Price",
            (p.price - COALESCE(s.discount,0)) * s.quantity_sold AS "Total",
            COALESCE(p.purchase_price,0) AS "Purchase Price",
            CASE WHEN s.is_return=0
                 THEN (p.price - COALESCE(s.discount,0) - COALESCE(p.purchase_price,0)) * s.quantity_sold
                 ELSE 0 END AS "Profit",
            CASE WHEN s.is_return=1 THEN 'Return' ELSE 'Sale' END AS "Type"
        FROM sale s
        JOIN product p ON s.product_id = p.id
        JOIN category c ON p.category_id = c.id
        WHERE s.sale_date BETWEEN :start AND :end
        ORDER BY s.sale_date DESC
    """)
    df = pd.read_sql(sql, db.engine, params={'start': start, 'end': end})
    if df.empty:
        flash('No data to export'); return redirect('/admin/sales')
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as w:
        df.to_excel(w, index=False, sheet_name='Sales')
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f'sales_{start_str}_to_{end_str}.xlsx')


# ── Stock Report ──────────────────────────────────────────────────────────────

@app.route('/admin/stock_report', methods=['GET', 'POST'])
def admin_stock_report():
    guard = admin_required()
    if guard: return guard
    categories      = Category.query.order_by(Category.name).all()
    selected_cat_id = request.form.get('cat_id', '') or request.args.get('cat_id', '')
    min_stock       = request.form.get('min_stock', '') or request.args.get('min_stock', '')

    filtered = []
    for cat in categories:
        prods = cat.products
        if selected_cat_id:
            if str(cat.id) != str(selected_cat_id): continue
        if min_stock:
            try: prods = [p for p in prods if p.quantity <= int(min_stock)]
            except Exception: pass
        filtered.append({'category': cat, 'products': prods})

    qty_by_cat = dict(
        db.session.query(Product.category_id,
                         func.coalesce(func.sum(Product.quantity), 0))
        .group_by(Product.category_id).all()
    )
    cat_names  = json.dumps([c.name for c in categories])
    cat_totals = json.dumps([int(qty_by_cat.get(c.id, 0)) for c in categories])

    return render_template('admin/stock_report.html',
        filtered=filtered, categories=categories,
        selected_cat_id=selected_cat_id, min_stock=min_stock,
        cat_names=cat_names, cat_totals=cat_totals)


# ── Low Stock ─────────────────────────────────────────────────────────────────

@app.route('/admin/lowstock')
def admin_lowstock():
    guard = admin_required()
    if guard: return guard
    page = request.args.get('page', 1, type=int)
    base = (
        Product.query
        .options(joinedload(Product.category))
        .filter(Product.quantity < Product.low_stock_limit)
        .order_by(Product.quantity.asc())
    )
    products, total_pages, total_count, page = _paginate(base, page)
    return render_template('admin/lowstock.html',
        products=products, page=page,
        total_pages=total_pages, total_count=total_count)


@app.route('/admin/lowstock/export')
def admin_lowstock_export():
    guard = admin_required()
    if guard: return guard
    sql = text("""
        SELECT p.name AS "Product", c.name AS "Category",
               p.quantity AS "Current Stock",
               p.low_stock_limit AS "Low Stock Limit",
               p.price AS "Sale Price",
               COALESCE(p.purchase_price,0) AS "Purchase Price"
        FROM product p JOIN category c ON p.category_id = c.id
        WHERE p.quantity < p.low_stock_limit
        ORDER BY p.quantity ASC
    """)
    df = pd.read_sql(sql, db.engine)
    if df.empty:
        flash('No low stock items'); return redirect('/admin/lowstock')
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as w:
        df.to_excel(w, index=False, sheet_name='Low Stock')
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name='low_stock_report.xlsx')


# ── Stock In Report ───────────────────────────────────────────────────────────

@app.route('/admin/stock_in')
def admin_stock_in():
    guard = admin_required()
    if guard: return guard
    start, end, start_str, end_str = _parse_dates()
    page = request.args.get('page', 1, type=int)
    records = []; total_added = 0; total_pages = 1; total_count = 0

    if start and end:
        total_added = db.session.query(
            func.coalesce(func.sum(StockIn.quantity_added), 0)
        ).filter(StockIn.date_added >= start, StockIn.date_added <= end).scalar() or 0

        rec_q = (
            StockIn.query
            .options(joinedload(StockIn.product).joinedload(Product.category))
            .filter(StockIn.date_added >= start, StockIn.date_added <= end)
            .order_by(StockIn.date_added.desc())
        )
        records, total_pages, total_count, page = _paginate(rec_q, page)
        if not records and page == 1:
            flash('No stock-in records in selected date range')
    elif start_str or end_str:
        flash('Invalid or missing dates')

    return render_template('admin/stock_in.html',
        records=records, start_str=start_str, end_str=end_str,
        total_added=int(total_added),
        page=page, total_pages=total_pages, total_count=total_count)


@app.route('/admin/stock_in/export')
def admin_stock_in_export():
    guard = admin_required()
    if guard: return guard
    start, end, start_str, end_str = _parse_dates()
    if not start:
        flash('Invalid date'); return redirect('/admin/stock_in')

    sql = text("""
        SELECT strftime('%Y-%m-%d %H:%M', si.date_added) AS "Date",
               p.name  AS "Product",
               c.name  AS "Category",
               si.quantity_added AS "Qty Added",
               COALESCE(p.purchase_price,0) AS "Purchase Price",
               COALESCE(p.purchase_price,0) * si.quantity_added AS "Total Value",
               si.note AS "Note"
        FROM stock_in si
        JOIN product p ON si.product_id = p.id
        JOIN category c ON p.category_id = c.id
        WHERE si.date_added BETWEEN :start AND :end
        ORDER BY si.date_added DESC
    """)
    df = pd.read_sql(sql, db.engine, params={'start': start, 'end': end})
    if df.empty:
        flash('No data to export'); return redirect('/admin/stock_in')
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as w:
        df.to_excel(w, index=False, sheet_name='Stock In')
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f'stock_in_{start_str}_to_{end_str}.xlsx')


# ── Stock Out Report ──────────────────────────────────────────────────────────

@app.route('/admin/stock_out')
def admin_stock_out():
    guard = admin_required()
    if guard: return guard
    start, end, start_str, end_str = _parse_dates()
    page = request.args.get('page', 1, type=int)
    sales = []; total_out = 0; total_value = 0.0; total_pages = 1; total_count = 0

    if start and end:
        agg = db.session.query(
            func.coalesce(func.sum(Sale.quantity_sold), 0),
            func.coalesce(func.sum(
                (Product.price - func.coalesce(Sale.discount, 0.0)) * Sale.quantity_sold
            ), 0.0)
        ).join(Product).filter(
            Sale.sale_date >= start, Sale.sale_date <= end,
            Sale.is_return == False
        ).first()
        total_out, total_value = int(agg[0]), float(agg[1])

        sale_q = (
            Sale.query
            .options(joinedload(Sale.product).joinedload(Product.category))
            .filter(Sale.sale_date >= start, Sale.sale_date <= end,
                    Sale.is_return == False)
            .order_by(Sale.sale_date.desc())
        )
        sales, total_pages, total_count, page = _paginate(sale_q, page)
        if not sales and page == 1:
            flash('No stock-out records in selected date range')
    elif start_str or end_str:
        flash('Invalid or missing dates')

    return render_template('admin/stock_out.html',
        sales=sales, start_str=start_str, end_str=end_str,
        total_out=total_out, total_value=total_value,
        page=page, total_pages=total_pages, total_count=total_count)


@app.route('/admin/stock_out/export')
def admin_stock_out_export():
    guard = admin_required()
    if guard: return guard
    start, end, start_str, end_str = _parse_dates()
    if not start:
        flash('Invalid date'); return redirect('/admin/stock_out')

    sql = text("""
        SELECT strftime('%Y-%m-%d %H:%M', s.sale_date) AS "Date",
               p.name AS "Product",
               c.name AS "Category",
               s.quantity_sold AS "Qty Out",
               p.price AS "Sale Price",
               COALESCE(s.discount,0) AS "Discount",
               p.price - COALESCE(s.discount,0) AS "Net Price",
               (p.price - COALESCE(s.discount,0)) * s.quantity_sold AS "Total Value"
        FROM sale s
        JOIN product p ON s.product_id = p.id
        JOIN category c ON p.category_id = c.id
        WHERE s.sale_date BETWEEN :start AND :end
          AND s.is_return = 0
        ORDER BY s.sale_date DESC
    """)
    df = pd.read_sql(sql, db.engine, params={'start': start, 'end': end})
    if df.empty:
        flash('No data to export'); return redirect('/admin/stock_out')
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as w:
        df.to_excel(w, index=False, sheet_name='Stock Out')
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f'stock_out_{start_str}_to_{end_str}.xlsx')


# ── Settings ──────────────────────────────────────────────────────────────────

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    guard = admin_required()
    if guard: return guard
    s = ShopSettings.query.first()
    if request.method == 'POST':
        s.shop_name      = request.form.get('shop_name',      '').strip()
        s.address        = request.form.get('address',        '').strip()
        s.contact1_name  = request.form.get('contact1_name',  '').strip()
        s.contact1_phone = request.form.get('contact1_phone', '').strip()
        s.contact2_name  = request.form.get('contact2_name',  '').strip()
        s.contact2_phone = request.form.get('contact2_phone', '').strip()
        s.bill_note      = request.form.get('bill_note',      '').strip()
        s.color_scheme   = request.form.get('color_scheme',   'blue')
        db.session.commit(); flash('Settings saved')
        return redirect('/admin/settings')
    return render_template('admin/settings.html', settings=s,
                           now=date.today().strftime('%d-%m-%Y'))


# ── Legacy redirects ──────────────────────────────────────────────────────────
@app.route('/admin/report',           methods=['GET', 'POST'])
def admin_report():        return redirect('/admin/sales')

@app.route('/admin/sales_stock',      methods=['GET', 'POST'])
def admin_sales_stock():   return redirect('/admin/sales')

@app.route('/admin/stock_by_category')
def admin_stock_by_category(): return redirect('/admin/stock_report')


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def _run_flask():
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    t = threading.Thread(target=_run_flask, daemon=True); t.start()
    time.sleep(1.5)
    import webview
    with app.app_context():
        s = ShopSettings.query.first()
        title = s.shop_name if s else 'POS'
    webview.create_window(title=title,
                          url='http://127.0.0.1:5000',
                          width=1280, height=800, resizable=True, min_size=(900, 600))
    webview.start()
