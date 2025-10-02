from flask import session
from models import Product

def get_cart():
    if 'cart' not in session:
        session['cart'] = {}
    return session['cart']

def get_cart_items():
    cart = get_cart()
    items = []
    total = 0
    for pid, data in cart.items():
        product = Product.query.get(int(pid))
        if product:
            # Get discount from cart data or product default
            discount = data.get('discount', product.discount)
            price_after_discount = max(product.price - discount, 0)
            subtotal = price_after_discount * data['qty']
            total += subtotal
            items.append({
                'id': int(pid),
                'name': product.name,
                'qty': data['qty'],
                'price': product.price,
                'discount': discount,
                'price_after_discount': price_after_discount,
                'max_qty': product.quantity
            })
    return items, total