# News AI Classification System

A full-stack Flask application for classifying news articles and detecting fake news using machine learning models. Includes authentication, role-based access control, MySQL integration, dark mode UI, and REST API.

## Features

- **Authentication & Authorization**
  - User registration with email validation
  - Session-based login/logout
  - Werkzeug password hashing
  - Role-based access control (Admin/User)
  - API token authentication

- **Classification**
  - Unified text classification interface
  - Fake news detection
  - Support for Hugging Face transformers with `.safetensors` format
  - Fallback to pickle-based sklearn models
  - Save results to MySQL linked to user account

- **Admin Panel**
  - User management (view, delete)
  - Classification history viewing & deletion
  - Category management (add, delete)
  - Admin-only dashboard

- **REST API**
  - `/api/login` — token-based authentication
  - `/api/classify` — submit text for classification
  - `/api/history` — view user classification history
  - `/api/admin/users` — list all users (admin only)
  - `/api/admin/results` — view all classification results (admin only)

- **UI**
  - Bootstrap 5 responsive design
  - Dark/Light mode toggle (saved to localStorage)
  - Clean, accessible forms and tables

## Project Structure

```
/app
  /__init__.py            # Flask app factory
  /config.py              # Configuration (loads .env)
  /database.py            # SQLAlchemy & Flask-Migrate instances
  /models.py              # ORM models (User, ArticleResult, Category)
  /utils.py               # Utility functions (password hashing, token auth)
  /auth.py                # Authentication blueprint
  /classification.py      # ML model loading & prediction logic
  /admin.py               # Admin panel blueprint
  /api.py                 # REST API blueprint
  /templates/             # Jinja2 templates
    base.html
    login.html
    register.html
    dashboard.html
    classify.html
    admin_dashboard.html
    admin_users.html
    admin_results.html
    admin_categories.html
  /static/
    /css/style.css        # Dark/light theme CSS
    theme.js              # Theme toggle script

/migrations/              # Flask-Migrate migration scripts (generated)
run.py                    # Application entry point
requirements.txt          # Python dependencies
.env.example              # Environment variable template
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```
FLASK_SECRET_KEY=your_secret_key_here
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DB=news_ai_system
```

### 3. Initialize Database

```bash
export FLASK_APP=run.py
flask db init
flask db migrate -m "initial"
flask db upgrade
```

This creates the MySQL schema with tables: `users`, `article_results`, `categories`.

### 4. Add ML Models

Place your models in the `app/models/` directory:

**Option A: Hugging Face `.safetensors` models**
```
app/models/
  classifier/
    config.json
    tokenizer.json
    pytorch_model.safetensors
    ...
  fake/
    config.json
    tokenizer.json
    pytorch_model.safetensors
    ...
```

**Option B: Pickle-based sklearn models**
```
app/models/
  classifier.pkl
  fake.pkl
```

Models are optional; the app gracefully degrades if they're missing (predictions return `null` confidence).

### 5. Run the Application

```bash
python run.py
```

Or using Flask CLI:

```bash
export FLASK_APP=run.py
flask run
```

Server starts at `http://localhost:5000`

## Usage

### Web Interface

1. **Register** at `/register` — create a new account
2. **Login** at `/login` — authenticate with email & password
3. **Classify** at `/classify` — paste article text and submit
4. **Admin Panel** at `/admin` — manage users, results, categories (admin-only)

### REST API

**Get Token:**
```bash
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'
```

Response:
```json
{"token": "abc123def456..."}
```

**Classify Article:**
```bash
curl -X POST http://localhost:5000/api/classify \
  -H "Authorization: Bearer abc123def456..." \
  -H "Content-Type: application/json" \
  -d '{"text":"Article content here..."}'
```

Response:
```json
{
  "category": "Politics",
  "category_confidence": 0.92,
  "fake_news_label": "real",
  "fake_confidence": 0.88
}
```

**Get User History:**
```bash
curl -X GET http://localhost:5000/api/history \
  -H "Authorization: Bearer abc123def456..."
```

**Admin: List All Users (admin token required):**
```bash
curl -X GET http://localhost:5000/api/admin/users \
  -H "Authorization: Bearer admin_token"
```

**Admin: View All Results (admin token required):**
```bash
curl -X GET http://localhost:5000/api/admin/results \
  -H "Authorization: Bearer admin_token"
```

## Database Schema

### users
- `id` (PK, int)
- `name` (string)
- `email` (string, unique)
- `password_hash` (string)
- `role` (enum: 'admin', 'user')
- `created_at` (datetime)
- `api_token` (string, unique)

### article_results
- `id` (PK, int)
- `user_id` (FK → users.id)
- `article_text` (text)
- `predicted_category` (string)
- `fake_news_label` (string)
- `category_confidence` (float)
- `fake_confidence` (float)
- `timestamp` (datetime)

### categories
- `id` (PK, int)
- `name` (string, unique)
- `description` (text)

## ML Model Integration

The app supports multiple model formats:

### Hugging Face Transformers + SafeTensors

Models are loaded via the `transformers` library. The app wraps HF pipelines with an `HFSklearnWrapper` class that provides a sklearn-like interface (`predict`, `predict_proba`, `classes_`).

**Example: Loading a local HF model**

Place a model folder at `app/models/classifier/` with `config.json`, `tokenizer.json`, and `pytorch_model.safetensors`, then the app will auto-load it.

### Sklearn Pickle Models

Legacy sklearn models saved as pickle are also supported. The app tries pickle first, then HF models.

**Graceful Fallback:** If no model is found, predictions return `None` category and `0.0` confidence.

## Configuration

All settings are loaded from `.env` via `app/config.py`:

- `FLASK_SECRET_KEY` — session/CSRF signing key (required for production)
- `MYSQL_HOST` — database host (default: localhost)
- `MYSQL_USER` — database user (default: root)
- `MYSQL_PASSWORD` — database password
- `MYSQL_DB` — database name (default: news_ai_system)

## Development

### Running Tests

```bash
# Set up test database
export FLASK_ENV=testing
flask db upgrade
```

### Creating an Admin User

Use the Flask shell:

```bash
export FLASK_APP=run.py
flask shell
```

Then in the shell:

```python
from app.models import User
from app.database import db
from app.utils import hash_password

admin = User(
    name='Admin',
    email='admin@example.com',
    password_hash=hash_password('admin_password'),
    role='admin'
)
db.session.add(admin)
db.session.commit()
```

## Troubleshooting

**"No module named 'app'"**
- Ensure you're running from the project root directory
- Check `FLASK_APP=run.py` is exported

**Database connection error**
- Verify MySQL is running
- Check `.env` credentials match your MySQL setup
- Ensure the database exists: `mysql -u root -p -e "CREATE DATABASE news_ai_system;"`

**Model loading fails**
- Check model path exists in `app/models/`
- Verify config.json, tokenizer.json, and safetensors files are present
- Check logs for more details

**Theme toggle not working**
- Clear browser cache/localStorage
- Ensure JavaScript is enabled
- Check console for errors (F12)

## License

MIT

## Author

News AI Team
