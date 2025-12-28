from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import request, jsonify
from .models import User
import os
import logging
import html
from flask import current_app, g

# --- LIME IMPORTS ---
import lime
from lime.lime_text import LimeTextExplainer
import torch
import torch.nn.functional as F
import numpy as np
# --------------------

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

logger = logging.getLogger(__name__)


def sanitize_text(text: str) -> str:
    if not text:
        return ''
    return html.escape(text)


def allowed_file(filename: str) -> bool:
    if not filename:
        return False
    _, ext = os.path.splitext(filename.lower())
    return ext in current_app.config.get('UPLOAD_EXTENSIONS', ['.txt'])


    
def explain_prediction(text: str, model_wrapper):
    """
    Generates a LIME explanation for the fake news prediction.
    """
    if not model_wrapper or not model_wrapper.pipeline:
        return None, []

    pipeline = model_wrapper.pipeline
    
    def predictor(texts):
        results = pipeline(texts, return_all_scores=True)
        all_probs = []
        for res in results:
            d = {item['label']: item['score'] for item in res}
            # ترتيب الاحتمالات: [Real, Fake]
            probs = [d.get('LABEL_0', 0.5), d.get('LABEL_1', 0.5)]
            all_probs.append(probs)
        return np.array(all_probs)


import html
import re
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# قائمة إضافية للكلمات التي لاحظت أنها تظهر وتزعجك
CUSTOM_STOP_WORDS = {
    'too', 'from', 'the', 'and', 'with', 'for', 'this', 'that', 
    'been', 'they', 'about', 'once', 'quot', 'amp', 'nbsp'
}

def explain_prediction(text: str, model_wrapper):
    if not model_wrapper or not model_wrapper.pipeline:
        return None, []

    # 1. تنظيف النص من الرموز الغريبة قبل إرساله لـ LIME
    # فك تشفير مثل &#x27; لتصبح '
    clean_text = html.unescape(text)
    # إزالة أي رموز غير مرغوب فيها متبقية باستخدام Regex
    clean_text = re.sub(r'\|#\w+;', '', clean_text) 
    clean_text = re.sub(r'\|quot', '', clean_text)

    pipeline = model_wrapper.pipeline
    
    def predictor(texts):
        results = pipeline(texts, return_all_scores=True)
        all_probs = []
        for res in results:
            d = {item['label']: item['score'] for item in res}
            probs = [d.get('LABEL_0', 0.5), d.get('LABEL_1', 0.5)]
            all_probs.append(probs)
        return np.array(all_probs)

    try:
        explainer = LimeTextExplainer(class_names=['Real', 'Fake'])
        
        # نستخدم النص النظيف هنا
        exp = explainer.explain_instance(
            clean_text[:1500], 
            predictor, 
            num_features=30, # نطلب عدد كبير لنصفي منهم الكلمات السيئة
            num_samples=250
        )
        
        raw_influence = exp.as_list()
        
        influence_list = []
        for word, weight in raw_influence:
            w_lower = word.lower()
            # فلتر صارم: ليس في StopWords، طوله أكثر من 2، وليس رقماً، وليس من القائمة المخصصة
            if (w_lower not in ENGLISH_STOP_WORDS and 
                w_lower not in CUSTOM_STOP_WORDS and 
                len(w_lower) > 2 and 
                not w_lower.isdigit()):
                
                influence_list.append({
                    'word': word,
                    'score': round(weight, 4),
                    'impact': 'Fake' if weight > 0 else 'Real'
                })
            
            if len(influence_list) >= 10: break
        
        return exp.as_html(), influence_list

    except Exception as e:
        print(f"LIME error: {e}")
        return None, []
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
    models = {'classifier': None, 'fake': None}
    try:
        from transformers import pipeline
        classifier_dir = os.path.join(app.root_path, 'models', 'classifier')
        fake_dir = os.path.join(app.root_path, 'models', 'fake')

        if os.path.isdir(classifier_dir) and os.listdir(classifier_dir):
            try:
                models['classifier'] = SimpleModelWrapper(pipeline('text-classification', model=classifier_dir, device=-1))
            except Exception:
                logger.exception('Failed to load classifier model')
                models['classifier'] = None

        if os.path.isdir(fake_dir) and os.listdir(fake_dir):
            try:
                models['fake'] = SimpleModelWrapper(pipeline('text-classification', model=fake_dir, device=-1))
            except Exception:
                logger.exception('Failed to load fake-news model')
                models['fake'] = None

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