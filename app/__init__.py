import os
from flask import Flask, g, render_template
from .config import Config
from .database import db, migrate
from .auth import auth_bp
from .admin import admin_bp
from .classification import classify_bp
from .api import api_bp
from .models import User, ArticleResult
from .utils import load_models
from flask_login import LoginManager, current_user

login_manager = LoginManager()


def create_app(config_object=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_object or Config)

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    # Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(classify_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    # Load ML models once and create default admin
    with app.app_context():
        load_models(app)

        admin_email = app.config.get("DEFAULT_ADMIN_EMAIL", "admin@gmail.com")
        admin_pw = app.config.get("DEFAULT_ADMIN_PASSWORD", "admin")
        if not User.query.filter_by(email=admin_email).first():
            admin = User(name="Administrator", email=admin_email)
            admin.set_password(admin_pw)
            admin.role = "admin"
            db.session.add(admin)
            db.session.commit()

    @app.before_request
    def load_current_user():
        from flask import session
        user_id = session.get("user_id")
        g.user = None
        if user_id:
            g.user = User.query.get(user_id)

    @app.route("/")
    def index():
        recent_results = []
        if current_user.is_authenticated:
            recent_results = (
                ArticleResult.query.filter_by(user_id=current_user.id)
                .order_by(ArticleResult.timestamp.desc())
                .limit(3)
                .all()
            )
        return render_template("dashboard.html", recent_results=recent_results)

    # Global error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception('Server error: %s', e)
        return render_template('500.html'), 500

    return app
