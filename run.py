from app import create_app
from app.config import Config
import os

app = create_app()

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    # Do not enable debug by default in production
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=debug)
