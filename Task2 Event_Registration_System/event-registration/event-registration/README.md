# EventHub — Event Registration System

A full-stack event registration platform built with **Flask** and **SQLite**, featuring user authentication, event browsing, registration management, and an organizer dashboard for creating events.

Matches Task 2 requirements:
- Backend using Flask to manage routes and logic
- Database models for events and user registrations (SQLite)
- API endpoints to view event list, event details, and submit registration forms
- Registrations linked to users and events — users can view/cancel their registrations
- **Optional (implemented):** Full authentication system + organizer role for creating events

## ✨ Features

- 🔐 **User authentication** — sign up, log in, log out (password hashing via Werkzeug)
- 🎟️ **Two roles** — regular attendees and event organizers
- 📊 **Dashboard** — stats overview, upcoming events, your registrations at a glance
- 📅 **Browse & register** for events, with live spot-count tracking
- ❌ **Cancel registration** anytime
- ➕ **Organizers can create new events** with title, description, location, date, and capacity
- 🌈 **Unique dark glassmorphism UI** with animated floating background shapes, gradient text, and smooth transitions
- 🔌 **JSON API** for events and registrations (see below)

## Project Structure
```
event-registration/
├── app.py                  # Flask app — routes, auth, database logic
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html            # Shared layout, navbar, flash messages
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── events.html          # Browse all events
│   ├── event_detail.html    # Single event + register/cancel
│   └── create_event.html    # Organizer-only event creation form
└── static/
    └── style.css             # Unique teal/cyan glassmorphism theme
```

## Setup Instructions

1. **Extract this zip** and open a terminal inside the `event-registration` folder.

2. **(Recommended) Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate      # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies** (only Flask is required — no extra packages):
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app:**
   ```bash
   python app.py
   ```

5. **Open your browser** and go to:
   ```
   http://localhost:8086
   ```

The SQLite database (`events.db`) is created automatically on first run, pre-seeded with a demo organizer account and 3 sample events.

## Demo Login

An organizer account is auto-created on first run so you can test event creation immediately:

- **Username:** `organizer`
- **Password:** `organizer123`

Or sign up your own account (check "I want to create and organize events" during signup to get organizer privileges).

## How It Works

1. **Sign up** or log in.
2. Land on your **Dashboard** — see stats, upcoming events, and your registrations.
3. Click **Browse Events** to see all events with live spot counts.
4. Click into any event to see full details and **Register**.
5. Registered events show up on your dashboard; cancel anytime from the event page.
6. If you're an organizer, click **+ Create Event** in the navbar to publish a new event.

## API Endpoints

| Method | Endpoint                  | Description                                  |
|--------|----------------------------|-----------------------------------------------|
| GET    | `/api/events`              | List all events with spot counts             |
| GET    | `/api/events/<id>`         | Get details for a single event                |
| GET    | `/api/my-registrations`    | List the logged-in user's active registrations (requires login) |

### Example
```bash
curl http://localhost:8086/api/events
```

## Notes
- Passwords are hashed with Werkzeug's `generate_password_hash` — never stored in plain text.
- Only users who checked "organizer" at signup (or the demo `organizer` account) can create events.
- To reset all data, delete `events.db` and restart the app — it regenerates with fresh demo data.
