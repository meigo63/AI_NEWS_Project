# Quick Start Guide

## 1. Install Dependencies (1 min)

```bash
pip install -r requirements.txt
```

## 2. Set Up Environment (1 min)

```bash
cp .env.example .env
# Edit .env with your MySQL credentials
nano .env
```

Required env vars:
```
FLASK_SECRET_KEY=any_secret_string
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DB=news_ai_system
```

## 3. Create MySQL Database (1 min)

```bash
mysql -u root -p -e "CREATE DATABASE news_ai_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

## 4. Initialize Database Schema (1 min)

```bash
export FLASK_APP=run.py
flask db init
flask db migrate -m "initial"
flask db upgrade
```

## 5. Add Your ML Models (optional)

Place models in `app/models/`:

**Hugging Face models:**
```
app/models/classifier/     # with config.json, tokenizer.json, model.safetensors
app/models/fake/           # with config.json, tokenizer.json, model.safetensors
```

**Or pickle models:**
```
app/models/classifier.pkl
app/models/fake.pkl
```

## 6. Run the App (1 min)

```bash
python run.py
```

App starts at: **http://localhost:5000**

## 7. Register & Login

1. Go to http://localhost:5000/register
2. Create an account
3. Login with your credentials
4. Navigate to `/classify` to test

## Create Admin User (optional)

```bash
export FLASK_APP=run.py
flask shell
```

In Flask shell:
```python
from app.models import User
from app.database import db
from app.utils import hash_password

admin = User(
    name='Admin',
    email='admin@example.com',
    password_hash=hash_password('admin123'),
    role='admin'
)
db.session.add(admin)
db.session.commit()
print("Admin user created!")
```

Then login with `admin@example.com` / `admin123` and access `/admin`.

## API Example

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' | jq -r '.token')

# Classify article
curl -X POST http://localhost:5000/api/classify \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Article text here..."}'
```

## Troubleshooting

**Port 5000 already in use?**
```bash
python run.py --port 5001
```

**MySQL connection error?**
- Check MySQL is running: `sudo service mysql status`
- Verify `.env` credentials
- Create DB if missing: `mysql -u root -p -e "CREATE DATABASE news_ai_system;"`

**Model not loading?**
- Check `app/models/` folder exists
- Verify HF model has config.json, tokenizer.json, safetensors
- App works without models (returns null predictions)

**See more in README.md**
