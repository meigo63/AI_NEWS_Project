from flask import Flask, render_template, redirect, url_for
from .config import Config
from .database import db, migrate
from .auth import auth_bp
from .admin import admin_bp
from .classification import classify_bp
from .api import api_bp
from flask_login import LoginManager, login_required, current_user
from .models import User, ArticleResult

login_manager = LoginManager()

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    # Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(classify_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/')
    def index():
        recent_results = []
        if current_user.is_authenticated:
            recent_results = ArticleResult.query.filter_by(user_id=current_user.id).order_by(ArticleResult.timestamp.desc()).limit(3).all()
        return render_template('dashboard.html', recent_results=recent_results)

    return app
