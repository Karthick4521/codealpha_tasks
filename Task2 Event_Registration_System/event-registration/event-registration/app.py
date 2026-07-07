from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'event-registration-secret-key-change-in-production'
DB_NAME = os.path.join(os.path.dirname(__file__), 'events.db')


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
            is_organizer INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            event_date TIMESTAMP NOT NULL,
            capacity INTEGER DEFAULT 50,
            organizer_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organizer_id) REFERENCES user (id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS registration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            status TEXT DEFAULT 'confirmed',
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user (id),
            FOREIGN KEY (event_id) REFERENCES event (id)
        )
    """)
    conn.commit()

    c.execute("SELECT COUNT(*) FROM event")
    if c.fetchone()[0] == 0:
        c.execute("SELECT id FROM user WHERE username = 'organizer'")
        row = c.fetchone()
        if row:
            organizer_id = row[0]
        else:
            pw_hash = generate_password_hash('organizer123')
            c.execute(
                "INSERT INTO user (username, email, password_hash, is_organizer) VALUES (?, ?, ?, 1)",
                ('organizer', 'organizer@demo.com', pw_hash)
            )
            organizer_id = c.lastrowid
            conn.commit()

        demo_events = [
            ('Tech Innovators Summit',
             'A gathering of the brightest minds in technology, featuring keynotes on AI, cloud computing, and the future of software.',
             'Chennai Trade Centre', '2026-08-15 10:00:00', 100, organizer_id),
            ('Campus Hackathon 2026',
             '24-hour coding marathon for students to build innovative solutions to real-world problems. Prizes worth Rs. 50,000!',
             'College Auditorium, Block A', '2026-08-22 09:00:00', 60, organizer_id),
            ('Career Fair & Networking Night',
             'Meet recruiters from top companies, attend resume workshops, and network with industry professionals.',
             'Main Campus Grounds', '2026-09-05 14:00:00', 200, organizer_id),
        ]
        c.executemany(
            "INSERT INTO event (title, description, location, event_date, capacity, organizer_id) VALUES (?, ?, ?, ?, ?, ?)",
            demo_events
        )
        conn.commit()

    conn.close()


def parse_dt(value):
    if isinstance(value, datetime):
        return value
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def event_spots_left(event_row, db):
    count = db.execute(
        "SELECT COUNT(*) FROM registration WHERE event_id = ? AND status = 'confirmed'",
        (event_row['id'],)
    ).fetchone()[0]
    return max(event_row['capacity'] - count, 0), count


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


def organizer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_organizer'):
            flash('Only organizers can create events.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_user():
    class CurrentUser:
        is_authenticated = 'user_id' in session
        username = session.get('username')
        is_organizer = session.get('is_organizer', False)
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
        is_organizer = 1 if request.form.get('is_organizer') == 'on' else 0

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
            "INSERT INTO user (username, email, password_hash, is_organizer) VALUES (?, ?, ?, ?)",
            (username, email, pw_hash, is_organizer)
        )
        db.commit()

        session['user_id'] = cur.lastrowid
        session['username'] = username
        session['is_organizer'] = bool(is_organizer)

        flash('Account created successfully!', 'success')
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
            session['is_organizer'] = bool(user['is_organizer'])
            return redirect(url_for('dashboard'))

        flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ---------------------------
# Main pages
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
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    upcoming_rows = db.execute(
        "SELECT * FROM event WHERE event_date >= ? ORDER BY event_date LIMIT 6", (now,)
    ).fetchall()

    upcoming_events = []
    for row in upcoming_rows:
        spots_left, _ = event_spots_left(row, db)
        upcoming_events.append({**dict(row), 'spots_left': spots_left, 'event_date': parse_dt(row['event_date'])})

    my_regs_rows = db.execute("""
        SELECT r.*, e.title as event_title, e.event_date as event_date
        FROM registration r JOIN event e ON r.event_id = e.id
        WHERE r.user_id = ? AND r.status = 'confirmed'
        ORDER BY e.event_date
    """, (session['user_id'],)).fetchall()

    my_registrations = []
    for row in my_regs_rows:
        my_registrations.append({
            'event_id': row['event_id'],
            'event_title': row['event_title'],
            'event_date': parse_dt(row['event_date']),
            'registered_at': parse_dt(row['registered_at'])
        })

    total_events = db.execute("SELECT COUNT(*) FROM event").fetchone()[0]
    events_created = db.execute(
        "SELECT COUNT(*) FROM event WHERE organizer_id = ?", (session['user_id'],)
    ).fetchone()[0]

    stats = {
        'total_events': total_events,
        'my_registrations': len(my_registrations),
        'events_created': events_created
    }

    return render_template('dashboard.html', upcoming_events=upcoming_events,
                           my_registrations=my_registrations, stats=stats)


@app.route('/events')
@login_required
def events():
    db = get_db()
    rows = db.execute("SELECT * FROM event ORDER BY event_date").fetchall()

    my_event_ids = {
        r['event_id'] for r in db.execute(
            "SELECT event_id FROM registration WHERE user_id = ? AND status = 'confirmed'",
            (session['user_id'],)
        ).fetchall()
    }

    all_events = []
    for row in rows:
        spots_left, _ = event_spots_left(row, db)
        organizer = db.execute("SELECT username FROM user WHERE id = ?", (row['organizer_id'],)).fetchone()
        all_events.append({
            **dict(row),
            'spots_left': spots_left,
            'event_date': parse_dt(row['event_date']),
            'organizer_username': organizer['username'] if organizer else 'Unknown'
        })

    return render_template('events.html', events=all_events, my_event_ids=my_event_ids)


@app.route('/events/<int:event_id>')
@login_required
def event_detail(event_id):
    db = get_db()
    row = db.execute("SELECT * FROM event WHERE id = ?", (event_id,)).fetchone()
    if not row:
        flash('Event not found.', 'error')
        return redirect(url_for('events'))

    spots_left, registered_count = event_spots_left(row, db)
    organizer = db.execute("SELECT username FROM user WHERE id = ?", (row['organizer_id'],)).fetchone()

    event = {
        **dict(row),
        'spots_left': spots_left,
        'registered_count': registered_count,
        'event_date': parse_dt(row['event_date']),
        'organizer_username': organizer['username'] if organizer else 'Unknown'
    }

    is_registered = db.execute(
        "SELECT 1 FROM registration WHERE user_id = ? AND event_id = ? AND status = 'confirmed'",
        (session['user_id'], event_id)
    ).fetchone() is not None

    return render_template('event_detail.html', event=event, is_registered=is_registered)


@app.route('/events/create', methods=['GET', 'POST'])
@login_required
@organizer_required
def create_event():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        location = request.form.get('location', '').strip()
        event_date_raw = request.form.get('event_date', '')
        capacity = request.form.get('capacity', 50)

        event_date_parsed = parse_dt(event_date_raw)
        if not event_date_parsed:
            flash('Invalid date format.', 'error')
            return redirect(url_for('create_event'))

        db = get_db()
        db.execute(
            "INSERT INTO event (title, description, location, event_date, capacity, organizer_id) VALUES (?, ?, ?, ?, ?, ?)",
            (title, description, location, event_date_parsed.strftime('%Y-%m-%d %H:%M:%S'), int(capacity), session['user_id'])
        )
        db.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('events'))

    return render_template('create_event.html')


# ---------------------------
# Registration actions
# ---------------------------
@app.route('/events/<int:event_id>/register', methods=['POST'])
@login_required
def register_for_event(event_id):
    db = get_db()
    event_row = db.execute("SELECT * FROM event WHERE id = ?", (event_id,)).fetchone()
    if not event_row:
        flash('Event not found.', 'error')
        return redirect(url_for('events'))

    existing = db.execute(
        "SELECT * FROM registration WHERE user_id = ? AND event_id = ?",
        (session['user_id'], event_id)
    ).fetchone()

    if existing:
        if existing['status'] == 'cancelled':
            db.execute("UPDATE registration SET status = 'confirmed' WHERE id = ?", (existing['id'],))
            db.commit()
            flash('Registration reactivated!', 'success')
        else:
            flash('You are already registered for this event.', 'info')
    else:
        spots_left, _ = event_spots_left(event_row, db)
        if spots_left <= 0:
            flash('Sorry, this event is full.', 'error')
            return redirect(url_for('event_detail', event_id=event_id))

        db.execute(
            "INSERT INTO registration (user_id, event_id, status) VALUES (?, ?, 'confirmed')",
            (session['user_id'], event_id)
        )
        db.commit()
        flash('Successfully registered!', 'success')

    return redirect(url_for('event_detail', event_id=event_id))


@app.route('/events/<int:event_id>/cancel', methods=['POST'])
@login_required
def cancel_registration(event_id):
    db = get_db()
    db.execute(
        "UPDATE registration SET status = 'cancelled' WHERE user_id = ? AND event_id = ? AND status = 'confirmed'",
        (session['user_id'], event_id)
    )
    db.commit()
    flash('Registration cancelled.', 'info')
    return redirect(request.referrer or url_for('dashboard'))


# ---------------------------
# JSON API endpoints (per task requirements)
# ---------------------------
@app.route('/api/events')
def api_events():
    db = get_db()
    rows = db.execute("SELECT * FROM event ORDER BY event_date").fetchall()
    result = []
    for row in rows:
        spots_left, _ = event_spots_left(row, db)
        result.append({
            'id': row['id'],
            'title': row['title'],
            'location': row['location'],
            'event_date': row['event_date'],
            'spots_left': spots_left,
            'capacity': row['capacity']
        })
    return jsonify(result)


@app.route('/api/events/<int:event_id>')
def api_event_detail(event_id):
    db = get_db()
    row = db.execute("SELECT * FROM event WHERE id = ?", (event_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Event not found'}), 404

    spots_left, _ = event_spots_left(row, db)
    organizer = db.execute("SELECT username FROM user WHERE id = ?", (row['organizer_id'],)).fetchone()

    return jsonify({
        'id': row['id'],
        'title': row['title'],
        'description': row['description'],
        'location': row['location'],
        'event_date': row['event_date'],
        'spots_left': spots_left,
        'capacity': row['capacity'],
        'organizer': organizer['username'] if organizer else None
    })


@app.route('/api/my-registrations')
@login_required
def api_my_registrations():
    db = get_db()
    rows = db.execute("""
        SELECT r.registered_at, e.id as event_id, e.title, e.event_date
        FROM registration r JOIN event e ON r.event_id = e.id
        WHERE r.user_id = ? AND r.status = 'confirmed'
    """, (session['user_id'],)).fetchall()

    return jsonify([{
        'event_id': row['event_id'],
        'title': row['title'],
        'event_date': row['event_date'],
        'registered_at': row['registered_at']
    } for row in rows])


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=8086)
