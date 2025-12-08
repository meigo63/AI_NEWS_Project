This folder is reserved for Flask-Migrate generated migration scripts.
Run the following after installing requirements and configuring `.env`:

```bash
flask db init
flask db migrate -m "initial"
flask db upgrade
```
