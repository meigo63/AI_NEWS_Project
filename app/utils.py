from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import request, jsonify
from .models import User
import os
import logging
import html
from flask import current_app, g

logger = logging.getLogger(__name__)


def sanitize_text(text: str) -> str:
    if not text:
        return ''
    # basic HTML-escape to avoid XSS; further sanitization can be added
    return html.escape(text)


def allowed_file(filename: str) -> bool:
    if not filename:
        return False
    _, ext = os.path.splitext(filename.lower())
    return ext in current_app.config.get('UPLOAD_EXTENSIONS', ['.txt'])


def explain_prediction(text: str) -> str:
    return "Explainability module coming soon"


class SimpleModelWrapper:
    def __init__(self, pipeline=None):
        self.pipeline = pipeline

    def predict(self, text: str):
        if not self.pipeline:
            return None
        try:
            return self.pipeline(text)
        except Exception as e:
            logger.exception("Model prediction failed")
            return None


def load_models(app):
    """Attempt to load transformer pipelines from disk. Store wrappers in app.config['ML_MODELS'].
    Gracefully continue if models are missing."""
    models = {'classifier': None, 'fake': None}
    try:
        from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
        # classifier
        classifier_dir = os.path.join(app.root_path, 'models', 'classifier')
        fake_dir = os.path.join(app.root_path, 'models', 'fake')

        if os.path.isdir(classifier_dir) and os.listdir(classifier_dir):
            try:
                models['classifier'] = SimpleModelWrapper(pipeline('text-classification', model=classifier_dir, device=-1))
            except Exception:
                logger.exception('Failed to load classifier model')
                models['classifier'] = None
        else:
            logger.warning('Classifier model not available at %s', classifier_dir)

        if os.path.isdir(fake_dir) and os.listdir(fake_dir):
            try:
                models['fake'] = SimpleModelWrapper(pipeline('text-classification', model=fake_dir, device=-1))
            except Exception:
                logger.exception('Failed to load fake-news model')
                models['fake'] = None
        else:
            logger.warning('Fake-news model not available at %s', fake_dir)

    except Exception:
        logger.exception('Transformers not available or failed to initialize')

    app.config['ML_MODELS'] = models
    return models

def hash_password(password: str) -> str:
    return generate_password_hash(password)

def verify_password(hash: str, password: str) -> bool:
    return check_password_hash(hash, password)

def token_auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization') or request.headers.get('X-API-Token')
        token = None
        if auth:
            if auth.startswith('Bearer '):
                token = auth.split(' ',1)[1]
            else:
                token = auth
        if not token:
            return jsonify({'error':'token required'}), 401
        user = User.query.filter_by(api_token=token).first()
        if not user:
            return jsonify({'error':'invalid token'}), 401
        request.user = user
        return fn(*args, **kwargs)
    return wrapper


def role_required(role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = getattr(g, 'user', None)
            if not user or user.role != role:
                return jsonify({'error': 'forbidden'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
