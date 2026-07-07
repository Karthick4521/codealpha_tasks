# TastePoint — Restaurant Management System

A full-stack restaurant management platform built with **Flask** and **SQLite**, handling orders, table status, reservations, and inventory — with a staff login system and admin controls.

Matches Task 3 requirements:
- Backend using Flask to handle restaurant operations (orders, tables, inventory)
- Database models for menu items, orders, tables, reservations, and inventory
- APIs for placing orders, reserving tables, updating inventory, and viewing menu
- Logic for order processing, table availability checks, and automatic inventory updates
- **Optional (implemented):** Reporting (daily sales) + admin-only access panel for menu & inventory

## ✨ Features

- 🔐 **Staff authentication** — login/signup with admin vs regular staff roles
- 📊 **Dashboard** — today's sales, active orders, reservations, low-stock alerts, table overview
- 🍽️ **Menu browsing** organized by category, with admin-only "Add Menu Item"
- 🪑 **Live table status** — available / reserved / occupied, with one-click "mark available"
- 📅 **Reservations** — book a table, seat guests, cancel — blocks booking on occupied tables
- 🧾 **Orders** — multi-item order builder, status flow (pending → preparing → served → paid), auto-calculates totals
- 📦 **Inventory auto-update** — placing an order automatically deducts ingredient stock; blocks the order if stock is insufficient
- ⚠️ **Low stock alerts** on the dashboard and inventory page
- 🌅 **Unique warm amber/gold glassmorphism UI** — distinct from other tasks' color themes, with a restaurant-appropriate serif heading font
- 🔌 **JSON API** for menu, tables, orders, inventory, and daily sales reports

## Project Structure
```
restaurant-management/
├── app.py                     # Flask app — routes, auth, database logic
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── login.html / register.html
│   ├── dashboard.html
│   ├── menu.html / create_menu_item.html
│   ├── tables.html
│   ├── reservations.html
│   ├── orders.html / order_detail.html
│   └── inventory.html
└── static/
    └── style.css                # Warm amber/gold glassmorphism theme
```

## Setup Instructions

1. **Extract this zip** and open a terminal inside the `restaurant-management` folder.

2. **(Recommended) Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate      # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies** (only Flask required):
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app:**
   ```bash
   python app.py
   ```

5. **Open your browser:**
   ```
   http://localhost:8087
   ```

The database (`restaurant.db`) is created automatically on first run, pre-seeded with a demo admin account, 6 menu items, 6 inventory ingredients, and 8 tables.

## Demo Login

- **Username:** `admin`
- **Password:** `admin123`

This gives you access to everything, including menu creation and inventory management.

## How It Works

1. **Log in** (or sign up — check "I am a manager/admin" for full access).
2. **Dashboard** shows today's sales, active orders, reservations, and any low-stock ingredients.
3. **Reservations** — book a table for a guest; occupied tables can't be double-booked.
4. **Orders** — pick a table and add menu items with quantities; placing the order automatically:
   - Checks if there's enough ingredient stock (blocks the order if not)
   - Deducts the used ingredients from inventory
   - Marks the table as occupied
5. Move orders through **pending → preparing → served → paid** from the order detail page; marking paid or cancelled frees the table again.
6. **Inventory** (admin only) — see stock levels and restock ingredients.

## API Endpoints

| Method | Endpoint                     | Description                                 |
|--------|-------------------------------|-----------------------------------------------|
| GET    | `/api/menu`                   | List all menu items                          |
| GET    | `/api/tables`                 | List all tables with current status           |
| GET    | `/api/orders`                 | List recent orders                            |
| POST   | `/api/orders`                 | Place an order — `{"table_id": 1, "items": [{"menu_item_id": 1, "quantity": 2}]}` |
| GET    | `/api/inventory`              | List all inventory items with stock levels    |
| GET    | `/api/reports/daily-sales`    | Today's total sales and order count           |

### Example
```bash
curl -X POST http://localhost:8087/api/orders \
  -H "Content-Type: application/json" \
  -d '{"table_id": 1, "items": [{"menu_item_id": 1, "quantity": 2}]}'
```

## Notes
- Passwords are hashed with Werkzeug — never stored in plain text.
- Only staff who checked "admin" at signup (or the demo `admin` account) can add menu items or manage inventory.
- To reset all data, delete `restaurant.db` and restart the app — it regenerates with fresh demo data.
