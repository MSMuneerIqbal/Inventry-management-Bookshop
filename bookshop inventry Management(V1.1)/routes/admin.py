from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from models.category import Category
from models.product import Product
from models.sale import Sale
from models import db
from datetime import datetime
import pandas as pd
import io

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
def admin():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    products = Product.query.join(Category).all()
    return render_template('admin/dashboard.html', products=products)

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['password'] == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin.admin'))
        flash('Invalid password')
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('user.home'))

@admin_bp.route('/add', methods=['GET', 'POST'])
def admin_add():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    categories = Category.query.all()
    if request.method == 'POST':
        name = request.form['name']
        author = request.form.get('author')
        category_id = int(request.form['category_id'])
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        purchase_price = request.form.get('purchase_price')
        purchase_price = float(purchase_price) if purchase_price else None
        existing = Product.query.filter_by(name=name, category_id=category_id).first()
        if existing:
            flash('Product with this name already exists in the selected category')
            return redirect(url_for('admin.admin_add'))
        product = Product(name=name, author=author, category_id=category_id, quantity=quantity, price=price, purchase_price=purchase_price)
        try:
            db.session.add(product)
            db.session.commit()
            flash('Product added')
            return redirect(url_for('admin.admin'))
        except:
            db.session.rollback()
            flash('Product with this name already exists in the selected category')
            return redirect(url_for('admin.admin_add'))
    return render_template('admin/add.html', categories=categories)

@admin_bp.route('/update/<int:pid>', methods=['GET', 'POST'])
def admin_update(pid):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    product = Product.query.get_or_404(pid)
    categories = Category.query.all()
    if request.method == 'POST':
        name = request.form['name']
        author = request.form.get('author')
        category_id = int(request.form['category_id'])
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        if name != product.name or category_id != product.category_id:
            existing = Product.query.filter_by(name=name, category_id=category_id).first()
            if existing and existing.id != pid:
                flash('Product with this name already exists in the selected category')
                return redirect(url_for('admin.admin_update', pid=pid))
        product.name = name
        product.author = author
        product.category_id = category_id
        product.quantity = quantity
        product.price = price
        try:
            db.session.commit()
            flash('Product updated')
            return redirect(url_for('admin.admin'))
        except:
            db.session.rollback()
            flash('Product with this name already exists in the selected category')
            return redirect(url_for('admin.admin_update', pid=pid))
    return render_template('admin/update.html', product=product, categories=categories)

@admin_bp.route('/delete/<int:pid>', methods=['POST'])
def admin_delete(pid):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    product = Product.query.get_or_404(pid)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted')
    return redirect(url_for('admin.admin'))

@admin_bp.route('/categories', methods=['GET'])
def admin_categories():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

@admin_bp.route('/add_category', methods=['GET', 'POST'])
def admin_add_category():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    if request.method == 'POST':
        name = request.form['name']
        category = Category(name=name)
        db.session.add(category)
        db.session.commit()
        flash('Category added')
        return redirect(url_for('admin.admin_categories'))
    return render_template('admin/add_category.html')

@admin_bp.route('/update_category/<int:cid>', methods=['GET', 'POST'])
def admin_update_category(cid):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    category = Category.query.get_or_404(cid)
    if request.method == 'POST':
        category.name = request.form['name']
        db.session.commit()
        flash('Category updated')
        return redirect(url_for('admin.admin_categories'))
    return render_template('admin/update_category.html', category=category)

@admin_bp.route('/delete_category/<int:cid>', methods=['POST'])
def admin_delete_category(cid):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    category = Category.query.get_or_404(cid)
    if Product.query.filter_by(category_id=cid).count() == 0:
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted')
    else:
        flash('Cannot delete category with products')
    return redirect(url_for('admin.admin_categories'))

@admin_bp.route('/lowstock')
def admin_lowstock():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    products = Product.query.filter(Product.quantity < 5).join(Category).order_by(Product.quantity.asc()).all()
    return render_template('admin/lowstock.html', products=products)

@admin_bp.route('/report', methods=['GET', 'POST'])
def admin_report():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_date = end_date.replace(hour=23, minute=59, second=59)
            if start_date > end_date:
                flash('Start date must be before end date')
                return redirect(url_for('admin.admin_report'))
        except ValueError:
            flash('Invalid date format')
            return redirect(url_for('admin.admin_report'))
        
        sales = Sale.query.join(Product).filter(
            Sale.sale_date >= start_date, Sale.sale_date <= end_date
        ).all()
        
        data = []
        for sale in sales:
            discount = sale.discount if hasattr(sale, 'discount') else (sale.product.discount or 0)
            sale_price = sale.product.price - discount
            data.append({
                'Date': sale.sale_date.strftime('%Y-%m-%d %H:%M'),
                'Product': sale.product.name,
                'Author': sale.product.author or 'N/A',
                'Category': sale.product.category.name,
                'Quantity': sale.quantity_sold,
                'Price': sale.product.price,
                'Discount': discount,
                'Sale Price': sale_price,
                'Total': sale.quantity_sold * sale_price,
                'Type': 'Return' if sale.is_return else 'Sale'
            })
        
        if not data:
            flash('No sales in the selected date range')
            return redirect(url_for('admin.admin_report'))
        
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sales Report')
        output.seek(0)
        
        filename = f'sales_report_{start_date_str}_to_{end_date_str}.xlsx'
        return send_file(output, as_attachment=True, download_name=filename)
    return render_template('admin/report.html')

@admin_bp.route('/sales_stock', methods=['GET', 'POST'])
def admin_sales_stock():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    sales = []
    start_date_str = None
    end_date_str = None
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_date = end_date.replace(hour=23, minute=59, second=59)
            if start_date > end_date:
                flash('Start date must be before end date')
                return redirect(url_for('admin.admin_sales_stock'))
        except ValueError:
            flash('Invalid date format')
            return redirect(url_for('admin.admin_sales_stock'))
        
        sales = Sale.query.join(Product).filter(
            Sale.sale_date >= start_date, Sale.sale_date <= end_date
        ).order_by(Sale.sale_date.desc()).all()
        
        if not sales:
            flash('No sales in the selected date range')
    
    return render_template('admin/sales_stock.html', sales=sales, start_date=start_date_str, end_date=end_date_str)

@admin_bp.route('/stock_by_category')
def admin_stock_by_category():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template('admin/stock_by_category.html', categories=categories)