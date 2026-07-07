from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'restaurant-management-secret-key-change-in-production'
DB_NAME = os.path.join(os.path.dirname(__file__), 'restaurant.db')


# ---------------------------
# Database helpers
# ---------------------------
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            quantity REAL NOT NULL DEFAULT 0,
            unit TEXT NOT NULL DEFAULT 'units',
            low_stock_threshold REAL NOT NULL DEFAULT 5
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS menu_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            inventory_item_id INTEGER,
            qty_per_order REAL NOT NULL DEFAULT 1,
            FOREIGN KEY (inventory_item_id) REFERENCES inventory_item (id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS restaurant_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_number INTEGER UNIQUE NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 4,
            status TEXT NOT NULL DEFAULT 'available'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS reservation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            phone TEXT,
            party_size INTEGER NOT NULL,
            reservation_time TIMESTAMP NOT NULL,
            status TEXT NOT NULL DEFAULT 'upcoming',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (table_id) REFERENCES restaurant_table (id),
            FOREIGN KEY (created_by) REFERENCES user (id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS restaurant_order (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            total_amount REAL NOT NULL DEFAULT 0,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (table_id) REFERENCES restaurant_table (id),
            FOREIGN KEY (created_by) REFERENCES user (id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS order_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price_at_order REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES restaurant_order (id),
            FOREIGN KEY (menu_item_id) REFERENCES menu_item (id)
        )
    """)

    conn.commit()

    # ---- Seed demo data ----
    c.execute("SELECT COUNT(*) FROM user")
    if c.fetchone()[0] == 0:
        admin_hash = generate_password_hash('admin123')
        c.execute(
            "INSERT INTO user (username, email, password_hash, is_admin) VALUES (?, ?, ?, 1)",
            ('admin', 'admin@demo.com', admin_hash)
        )
        conn.commit()

    c.execute("SELECT COUNT(*) FROM inventory_item")
    if c.fetchone()[0] == 0:
        inventory = [
            ('Chicken', 40, 'kg', 8),
            ('Basmati Rice', 60, 'kg', 10),
            ('Paneer', 15, 'kg', 5),
            ('Tomatoes', 25, 'kg', 6),
            ('Flour', 30, 'kg', 8),
            ('Cheese', 12, 'kg', 4),
        ]
        c.executemany(
            "INSERT INTO inventory_item (name, quantity, unit, low_stock_threshold) VALUES (?, ?, ?, ?)",
            inventory
        )
        conn.commit()

    c.execute("SELECT COUNT(*) FROM menu_item")
    if c.fetchone()[0] == 0:
        chicken_id = c.execute("SELECT id FROM inventory_item WHERE name = 'Chicken'").fetchone()[0]
        rice_id = c.execute("SELECT id FROM inventory_item WHERE name = 'Basmati Rice'").fetchone()[0]
        paneer_id = c.execute("SELECT id FROM inventory_item WHERE name = 'Paneer'").fetchone()[0]
        tomato_id = c.execute("SELECT id FROM inventory_item WHERE name = 'Tomatoes'").fetchone()[0]
        flour_id = c.execute("SELECT id FROM inventory_item WHERE name = 'Flour'").fetchone()[0]
        cheese_id = c.execute("SELECT id FROM inventory_item WHERE name = 'Cheese'").fetchone()[0]

        menu = [
            ('Chicken Biryani', 'Fragrant basmati rice slow-cooked with tender chicken and warm spices.', 249, 'Main Course', chicken_id, 0.4),
            ('Paneer Butter Masala', 'Cottage cheese cubes simmered in a rich, creamy tomato gravy.', 199, 'Main Course', paneer_id, 0.25),
            ('Margherita Pizza', 'Classic wood-fired pizza with fresh tomato, mozzarella, and basil.', 279, 'Main Course', cheese_id, 0.2),
            ('Tomato Soup', 'Velvety roasted tomato soup finished with cream and herbs.', 99, 'Starters', tomato_id, 0.3),
            ('Butter Naan', 'Soft, fluffy Indian flatbread brushed with butter.', 49, 'Breads', flour_id, 0.15),
            ('Chicken Tikka', 'Char-grilled marinated chicken skewers with mint chutney.', 219, 'Starters', chicken_id, 0.3),
        ]
        c.executemany(
            "INSERT INTO menu_item (name, description, price, category, inventory_item_id, qty_per_order) VALUES (?, ?, ?, ?, ?, ?)",
            menu
        )
        conn.commit()

    c.execute("SELECT COUNT(*) FROM restaurant_table")
    if c.fetchone()[0] == 0:
        tables = [(i, 4 if i % 2 == 0 else 2, 'available') for i in range(1, 9)]
        c.executemany(
            "INSERT INTO restaurant_table (table_number, capacity, status) VALUES (?, ?, ?)",
            tables
        )
        conn.commit()

    conn.close()


def parse_dt(value):
    if isinstance(value, datetime):
        return value
    if value is None:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S.%f'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


# ---------------------------
# Auth helpers
# ---------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Only admins can access this page.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_user():
    class CurrentUser:
        is_authenticated = 'user_id' in session
        username = session.get('username')
        is_admin = session.get('is_admin', False)
    return {'current_user': CurrentUser()}


# ---------------------------
# Auth routes
# ---------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        is_admin = 1 if request.form.get('is_admin') == 'on' else 0

        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))

        db = get_db()
        if db.execute("SELECT 1 FROM user WHERE username = ?", (username,)).fetchone():
            flash('Username already taken.', 'error')
            return redirect(url_for('register'))
        if db.execute("SELECT 1 FROM user WHERE email = ?", (email,)).fetchone():
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))

        pw_hash = generate_password_hash(password)
        cur = db.execute(
            "INSERT INTO user (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
            (username, email, pw_hash, is_admin)
        )
        db.commit()

        session['user_id'] = cur.lastrowid
        session['username'] = username
        session['is_admin'] = bool(is_admin)

        flash('Staff account created successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        db = get_db()
        user = db.execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            return redirect(url_for('dashboard'))

        flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ---------------------------
# Dashboard
# ---------------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    today = datetime.utcnow().strftime('%Y-%m-%d')

    todays_sales = db.execute(
        "SELECT COALESCE(SUM(total_amount), 0) FROM restaurant_order WHERE date(created_at) = ? AND status != 'cancelled'",
        (today,)
    ).fetchone()[0]

    active_orders = db.execute(
        "SELECT COUNT(*) FROM restaurant_order WHERE status IN ('pending', 'preparing')"
    ).fetchone()[0]

    todays_reservations = db.execute(
        "SELECT COUNT(*) FROM reservation WHERE date(reservation_time) = ? AND status != 'cancelled'",
        (today,)
    ).fetchone()[0]

    low_stock_items = db.execute(
        "SELECT * FROM inventory_item WHERE quantity <= low_stock_threshold ORDER BY quantity"
    ).fetchall()

    recent_orders_rows = db.execute("""
        SELECT o.*, t.table_number FROM restaurant_order o
        JOIN restaurant_table t ON o.table_id = t.id
        ORDER BY o.created_at DESC LIMIT 6
    """).fetchall()
    recent_orders = [{**dict(r), 'created_at': parse_dt(r['created_at'])} for r in recent_orders_rows]

    upcoming_reservations_rows = db.execute("""
        SELECT r.*, t.table_number FROM reservation r
        JOIN restaurant_table t ON r.table_id = t.id
        WHERE r.status = 'upcoming'
        ORDER BY r.reservation_time LIMIT 6
    """).fetchall()
    upcoming_reservations = [{**dict(r), 'reservation_time': parse_dt(r['reservation_time'])} for r in upcoming_reservations_rows]

    tables = db.execute("SELECT * FROM restaurant_table ORDER BY table_number").fetchall()

    stats = {
        'todays_sales': todays_sales,
        'active_orders': active_orders,
        'todays_reservations': todays_reservations,
        'low_stock_count': len(low_stock_items)
    }

    return render_template('dashboard.html', stats=stats, low_stock_items=low_stock_items,
                           recent_orders=recent_orders, upcoming_reservations=upcoming_reservations,
                           tables=tables)


# ---------------------------
# Menu
# ---------------------------
@app.route('/menu')
@login_required
def menu():
    db = get_db()
    items = db.execute("""
        SELECT m.*, i.quantity as stock_qty, i.name as ingredient_name
        FROM menu_item m LEFT JOIN inventory_item i ON m.inventory_item_id = i.id
        ORDER BY m.category, m.name
    """).fetchall()

    categorized = {}
    for item in items:
        categorized.setdefault(item['category'], []).append(item)

    return render_template('menu.html', categorized=categorized)


@app.route('/menu/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_menu_item():
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', 0)
        category = request.form.get('category', '').strip()
        inventory_item_id = request.form.get('inventory_item_id') or None
        qty_per_order = request.form.get('qty_per_order', 1)

        db.execute(
            "INSERT INTO menu_item (name, description, price, category, inventory_item_id, qty_per_order) VALUES (?, ?, ?, ?, ?, ?)",
            (name, description, float(price), category, inventory_item_id, float(qty_per_order))
        )
        db.commit()
        flash('Menu item added successfully!', 'success')
        return redirect(url_for('menu'))

    inventory_items = db.execute("SELECT * FROM inventory_item ORDER BY name").fetchall()
    return render_template('create_menu_item.html', inventory_items=inventory_items)


# ---------------------------
# Tables & Reservations
# ---------------------------
@app.route('/tables')
@login_required
def tables():
    db = get_db()
    all_tables = db.execute("SELECT * FROM restaurant_table ORDER BY table_number").fetchall()
    return render_template('tables.html', tables=all_tables)


@app.route('/reservations')
@login_required
def reservations():
    db = get_db()
    rows = db.execute("""
        SELECT r.*, t.table_number FROM reservation r
        JOIN restaurant_table t ON r.table_id = t.id
        ORDER BY r.reservation_time DESC
    """).fetchall()
    all_reservations = [{**dict(r), 'reservation_time': parse_dt(r['reservation_time'])} for r in rows]
    all_tables = db.execute("SELECT * FROM restaurant_table ORDER BY table_number").fetchall()
    return render_template('reservations.html', reservations=all_reservations, tables=all_tables)


@app.route('/reservations/create', methods=['POST'])
@login_required
def create_reservation():
    db = get_db()
    table_id = request.form.get('table_id')
    customer_name = request.form.get('customer_name', '').strip()
    phone = request.form.get('phone', '').strip()
    party_size = request.form.get('party_size', 1)
    reservation_time_raw = request.form.get('reservation_time', '')

    reservation_time = parse_dt(reservation_time_raw)
    if not reservation_time:
        flash('Invalid date/time.', 'error')
        return redirect(url_for('reservations'))

    table = db.execute("SELECT * FROM restaurant_table WHERE id = ?", (table_id,)).fetchone()
    if not table:
        flash('Table not found.', 'error')
        return redirect(url_for('reservations'))

    if table['status'] == 'occupied':
        flash(f"Table {table['table_number']} is currently occupied.", 'error')
        return redirect(url_for('reservations'))

    db.execute(
        "INSERT INTO reservation (table_id, customer_name, phone, party_size, reservation_time, status, created_by) VALUES (?, ?, ?, ?, ?, 'upcoming', ?)",
        (table_id, customer_name, phone, int(party_size), reservation_time.strftime('%Y-%m-%d %H:%M:%S'), session['user_id'])
    )
    db.execute("UPDATE restaurant_table SET status = 'reserved' WHERE id = ?", (table_id,))
    db.commit()

    flash(f"Reservation created for {customer_name}!", 'success')
    return redirect(url_for('reservations'))


@app.route('/reservations/<int:res_id>/seat', methods=['POST'])
@login_required
def seat_reservation(res_id):
    db = get_db()
    res = db.execute("SELECT * FROM reservation WHERE id = ?", (res_id,)).fetchone()
    if res:
        db.execute("UPDATE reservation SET status = 'seated' WHERE id = ?", (res_id,))
        db.execute("UPDATE restaurant_table SET status = 'occupied' WHERE id = ?", (res['table_id'],))
        db.commit()
        flash('Guests seated!', 'success')
    return redirect(url_for('reservations'))


@app.route('/reservations/<int:res_id>/cancel', methods=['POST'])
@login_required
def cancel_reservation(res_id):
    db = get_db()
    res = db.execute("SELECT * FROM reservation WHERE id = ?", (res_id,)).fetchone()
    if res:
        db.execute("UPDATE reservation SET status = 'cancelled' WHERE id = ?", (res_id,))
        db.execute("UPDATE restaurant_table SET status = 'available' WHERE id = ?", (res['table_id'],))
        db.commit()
        flash('Reservation cancelled.', 'info')
    return redirect(url_for('reservations'))


@app.route('/tables/<int:table_id>/free', methods=['POST'])
@login_required
def free_table(table_id):
    db = get_db()
    db.execute("UPDATE restaurant_table SET status = 'available' WHERE id = ?", (table_id,))
    db.commit()
    flash('Table marked as available.', 'success')
    return redirect(url_for('tables'))


# ---------------------------
# Orders
# ---------------------------
@app.route('/orders')
@login_required
def orders():
    db = get_db()
    rows = db.execute("""
        SELECT o.*, t.table_number FROM restaurant_order o
        JOIN restaurant_table t ON o.table_id = t.id
        ORDER BY o.created_at DESC
    """).fetchall()
    all_orders = [{**dict(r), 'created_at': parse_dt(r['created_at'])} for r in rows]

    all_tables = db.execute("SELECT * FROM restaurant_table WHERE status != 'available' OR status = 'available' ORDER BY table_number").fetchall()
    menu_items = db.execute("SELECT * FROM menu_item ORDER BY category, name").fetchall()

    return render_template('orders.html', orders=all_orders, tables=all_tables, menu_items=menu_items)


@app.route('/orders/create', methods=['POST'])
@login_required
def create_order():
    db = get_db()
    table_id = request.form.get('table_id')
    item_ids = request.form.getlist('menu_item_id')
    quantities = request.form.getlist('quantity')

    if not item_ids:
        flash('Please select at least one menu item.', 'error')
        return redirect(url_for('orders'))

    # Validate stock availability first
    order_lines = []
    for item_id, qty in zip(item_ids, quantities):
        qty = int(qty)
        if qty <= 0:
            continue
        menu_item = db.execute("SELECT * FROM menu_item WHERE id = ?", (item_id,)).fetchone()
        if not menu_item:
            continue

        if menu_item['inventory_item_id']:
            inv = db.execute("SELECT * FROM inventory_item WHERE id = ?", (menu_item['inventory_item_id'],)).fetchone()
            required = menu_item['qty_per_order'] * qty
            if inv and inv['quantity'] < required:
                flash(f"Not enough {inv['name']} in stock for {menu_item['name']}.", 'error')
                return redirect(url_for('orders'))

        order_lines.append((menu_item, qty))

    if not order_lines:
        flash('No valid items to order.', 'error')
        return redirect(url_for('orders'))

    total = sum(item['price'] * qty for item, qty in order_lines)

    cur = db.execute(
        "INSERT INTO restaurant_order (table_id, status, total_amount, created_by) VALUES (?, 'pending', ?, ?)",
        (table_id, total, session['user_id'])
    )
    order_id = cur.lastrowid

    for item, qty in order_lines:
        db.execute(
            "INSERT INTO order_item (order_id, menu_item_id, quantity, price_at_order) VALUES (?, ?, ?, ?)",
            (order_id, item['id'], qty, item['price'])
        )
        # Auto-update inventory
        if item['inventory_item_id']:
            consumed = item['qty_per_order'] * qty
            db.execute(
                "UPDATE inventory_item SET quantity = quantity - ? WHERE id = ?",
                (consumed, item['inventory_item_id'])
            )

    db.execute("UPDATE restaurant_table SET status = 'occupied' WHERE id = ?", (table_id,))
    db.commit()

    flash('Order placed successfully!', 'success')
    return redirect(url_for('order_detail', order_id=order_id))


@app.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    db = get_db()
    order_row = db.execute("""
        SELECT o.*, t.table_number FROM restaurant_order o
        JOIN restaurant_table t ON o.table_id = t.id
        WHERE o.id = ?
    """, (order_id,)).fetchone()

    if not order_row:
        flash('Order not found.', 'error')
        return redirect(url_for('orders'))

    order = {**dict(order_row), 'created_at': parse_dt(order_row['created_at'])}

    items = db.execute("""
        SELECT oi.*, m.name as item_name FROM order_item oi
        JOIN menu_item m ON oi.menu_item_id = m.id
        WHERE oi.order_id = ?
    """, (order_id,)).fetchall()

    return render_template('order_detail.html', order=order, items=items)


@app.route('/orders/<int:order_id>/status', methods=['POST'])
@login_required
def update_order_status(order_id):
    db = get_db()
    new_status = request.form.get('status')
    valid_statuses = ('pending', 'preparing', 'served', 'paid', 'cancelled')

    if new_status in valid_statuses:
        db.execute("UPDATE restaurant_order SET status = ? WHERE id = ?", (new_status, order_id))

        if new_status in ('paid', 'cancelled'):
            order_row = db.execute("SELECT table_id FROM restaurant_order WHERE id = ?", (order_id,)).fetchone()
            if order_row:
                db.execute("UPDATE restaurant_table SET status = 'available' WHERE id = ?", (order_row['table_id'],))

        db.commit()
        flash(f'Order marked as {new_status}.', 'success')

    return redirect(url_for('order_detail', order_id=order_id))


# ---------------------------
# Inventory
# ---------------------------
@app.route('/inventory')
@login_required
@admin_required
def inventory():
    db = get_db()
    items = db.execute("SELECT * FROM inventory_item ORDER BY name").fetchall()
    return render_template('inventory.html', items=items)


@app.route('/inventory/<int:item_id>/restock', methods=['POST'])
@login_required
@admin_required
def restock_inventory(item_id):
    db = get_db()
    amount = request.form.get('amount', 0)
    try:
        amount = float(amount)
    except ValueError:
        amount = 0

    if amount > 0:
        db.execute("UPDATE inventory_item SET quantity = quantity + ? WHERE id = ?", (amount, item_id))
        db.commit()
        flash('Stock updated successfully!', 'success')

    return redirect(url_for('inventory'))


# ---------------------------
# JSON API endpoints (per task requirements)
# ---------------------------
@app.route('/api/menu')
def api_menu():
    db = get_db()
    items = db.execute("SELECT * FROM menu_item ORDER BY category, name").fetchall()
    return jsonify([{
        'id': i['id'], 'name': i['name'], 'description': i['description'],
        'price': i['price'], 'category': i['category']
    } for i in items])


@app.route('/api/tables')
def api_tables():
    db = get_db()
    rows = db.execute("SELECT * FROM restaurant_table ORDER BY table_number").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/orders', methods=['GET', 'POST'])
def api_orders():
    db = get_db()
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        table_id = data.get('table_id')
        items = data.get('items', [])

        if not table_id or not items:
            return jsonify({'error': 'table_id and items are required'}), 400

        total = 0
        for entry in items:
            menu_item = db.execute("SELECT * FROM menu_item WHERE id = ?", (entry.get('menu_item_id'),)).fetchone()
            if not menu_item:
                return jsonify({'error': f"Menu item {entry.get('menu_item_id')} not found"}), 404
            total += menu_item['price'] * entry.get('quantity', 1)

        cur = db.execute(
            "INSERT INTO restaurant_order (table_id, status, total_amount) VALUES (?, 'pending', ?)",
            (table_id, total)
        )
        order_id = cur.lastrowid

        for entry in items:
            menu_item = db.execute("SELECT * FROM menu_item WHERE id = ?", (entry.get('menu_item_id'),)).fetchone()
            qty = entry.get('quantity', 1)
            db.execute(
                "INSERT INTO order_item (order_id, menu_item_id, quantity, price_at_order) VALUES (?, ?, ?, ?)",
                (order_id, menu_item['id'], qty, menu_item['price'])
            )
            if menu_item['inventory_item_id']:
                consumed = menu_item['qty_per_order'] * qty
                db.execute("UPDATE inventory_item SET quantity = quantity - ? WHERE id = ?",
                          (consumed, menu_item['inventory_item_id']))

        db.execute("UPDATE restaurant_table SET status = 'occupied' WHERE id = ?", (table_id,))
        db.commit()

        return jsonify({'order_id': order_id, 'total_amount': total}), 201

    rows = db.execute("SELECT * FROM restaurant_order ORDER BY created_at DESC LIMIT 50").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/inventory')
def api_inventory():
    db = get_db()
    rows = db.execute("SELECT * FROM inventory_item ORDER BY name").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/reports/daily-sales')
def api_daily_sales():
    db = get_db()
    today = datetime.utcnow().strftime('%Y-%m-%d')
    total = db.execute(
        "SELECT COALESCE(SUM(total_amount), 0) FROM restaurant_order WHERE date(created_at) = ? AND status != 'cancelled'",
        (today,)
    ).fetchone()[0]
    order_count = db.execute(
        "SELECT COUNT(*) FROM restaurant_order WHERE date(created_at) = ? AND status != 'cancelled'",
        (today,)
    ).fetchone()[0]
    return jsonify({'date': today, 'total_sales': total, 'order_count': order_count})


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=8087)
