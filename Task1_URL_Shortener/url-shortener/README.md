# Simple URL Shortener

A basic URL shortener built with **Flask** and **SQLite**, matching Task 1 requirements:

- Backend server using Flask
- API endpoint to accept long URLs and generate a unique short code
- Stores the mapping of short code ↔ original URL in a SQLite database
- Redirect route: visiting the short URL takes you to the original long URL
- Optional basic frontend to input long URLs and view the shortened version

## Project Structure
```
url-shortener/
├── app.py                # Flask app (routes + logic)
├── database.db           # SQLite database (auto-created on first run)
├── requirements.txt
├── templates/
│   ├── index.html         # Frontend page
│   └── 404.html           # Error page for invalid short codes
└── static/
    ├── style.css
    └── script.js
```

## Setup Instructions

1. **Extract the zip** and open a terminal inside the `url-shortener` folder.

2. **(Recommended) Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate      # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app:**
   ```bash
   python app.py
   ```

5. **Open your browser** and go to:
   ```
   http://localhost:5000
   ```

The SQLite database file (`database.db`) is created automatically the first time you run the app.

## How It Works

- Paste any long URL into the input box on the homepage and click **Shorten**.
- The backend generates a random 6-character short code (e.g. `aZ3kD9`) and stores it with the original URL.
- You get a short URL like `http://localhost:5000/aZ3kD9`.
- Visiting that short URL redirects you to the original long URL.
- The homepage also lists all previously shortened URLs.

## API Endpoints

| Method | Endpoint             | Description                          |
|--------|----------------------|---------------------------------------|
| POST   | `/api/shorten`       | Body: `{ "url": "https://..." }` → returns short code & short URL |
| GET    | `/api/urls`          | Lists all stored URL mappings         |
| GET    | `/<short_code>`      | Redirects to the original long URL    |

### Example (using curl)
```bash
curl -X POST http://localhost:5000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.example.com/some/very/long/path"}'
```

## Notes
- If the same URL is submitted twice, the existing short code is reused instead of creating a duplicate.
- URLs without `http://` or `https://` are automatically prefixed with `https://`.
- To reset all data, simply delete `database.db` and restart the app — it will be recreated automatically.
