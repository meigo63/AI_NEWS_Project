import os
import pickle
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from .models import ArticleResult
from .database import db
from flask_login import login_required, current_user

classify_bp = Blueprint('classify', __name__, template_folder='templates')

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
classifier = None
fake_detector = None


class HFSklearnWrapper:
    def __init__(self, pipeline, labels=None):
        self.pipeline = pipeline
        self._labels = labels

    @property
    def classes_(self):
        if self._labels:
            return self._labels
        try:
            res = self.pipeline('test', return_all_scores=True)[0]
            self._labels = [r['label'] for r in res]
            return self._labels
        except Exception:
            return []

    def predict(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        out = []
        for t in texts:
            r = self.pipeline(t)
            if isinstance(r, list):
                out.append(r[0]['label'])
            else:
                out.append(r['label'])
        return out

    def predict_proba(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        all_scores = self.pipeline(texts, return_all_scores=True)
        probs = []
        for scores in all_scores:
            scores_map = {s['label']: s['score'] for s in scores}
            ordered = [scores_map.get(lbl, 0.0) for lbl in self.classes_]
            probs.append(ordered)
        import numpy as _np
        return _np.array(probs)


def try_load_hf_model(model_path):
    try:
        from transformers import pipeline
        if os.path.isfile(model_path) and model_path.endswith('.safetensors'):
            model_dir = os.path.dirname(model_path)
        else:
            model_dir = model_path
        nlp = pipeline('text-classification', model=model_dir, tokenizer=model_dir, return_all_scores=True)
        wrapper = HFSklearnWrapper(nlp)
        _ = wrapper.classes_
        return wrapper
    except Exception:
        return None


def load_classification_model():
    global classifier
    if classifier is not None:
        return classifier
    pkl = os.path.join(MODEL_DIR, 'classifier.pkl')
    if os.path.exists(pkl):
        try:
            classifier = pickle.load(open(pkl, 'rb'))
            return classifier
        except Exception:
            classifier = None
    hf_file = os.path.join(MODEL_DIR, 'classifier.safetensors')
    hf_dir = os.path.join(MODEL_DIR, 'classifier')
    for candidate in (hf_file, hf_dir):
        if os.path.exists(candidate):
            classifier = try_load_hf_model(candidate)
            if classifier:
                return classifier
    return None


def load_fake_news_model():
    global fake_detector
    if fake_detector is not None:
        return fake_detector
    pkl = os.path.join(MODEL_DIR, 'fake.pkl')
    if os.path.exists(pkl):
        try:
            fake_detector = pickle.load(open(pkl, 'rb'))
            return fake_detector
        except Exception:
            fake_detector = None
    hf_file = os.path.join(MODEL_DIR, 'fake.safetensors')
    hf_dir = os.path.join(MODEL_DIR, 'fake')
    for candidate in (hf_file, hf_dir):
        if os.path.exists(candidate):
            fake_detector = try_load_hf_model(candidate)
            if fake_detector:
                return fake_detector
    return None


def predict_category(text):
    model = load_classification_model()
    if not model:
        return None, 0.0
    try:
        probs = model.predict_proba([text])[0]
        import numpy as _np
        idx = int(_np.argmax(probs))
        return model.classes_[idx], float(probs[idx])
    except Exception:
        try:
            label = model.predict([text])[0]
            return label, 0.0
        except Exception:
            return None, 0.0


def predict_fake_news(text):
    model = load_fake_news_model()
    if not model:
        return None, 0.0
    try:
        probs = model.predict_proba([text])[0]
        import numpy as _np
        idx = int(_np.argmax(probs))
        label = model.classes_[idx]
        return label, float(probs[idx])
    except Exception:
        try:
            label = model.predict([text])[0]
            return label, 0.0
        except Exception:
            return None, 0.0


@classify_bp.route('/classify', methods=['GET', 'POST'])
def classify_page():
    # Check if user has used the anonymous one-time access
    has_used_anonymous = session.get('used_anonymous_classify', False)
    is_authenticated = current_user.is_authenticated
    
    # If not logged in and already used anonymous access, require login
    if not is_authenticated and has_used_anonymous:
        flash('You have used your one-time classification. Please login to continue.', 'info')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        text = request.form.get('article_text')
        cat, cat_conf = predict_category(text)
        fake_label, fake_conf = predict_fake_news(text)

        # Only save to database if logged in
        if is_authenticated:
            result = ArticleResult(
                user_id=current_user.id,
                article_text=text,
                predicted_category=cat,
                fake_news_label=fake_label,
                category_confidence=cat_conf,
                fake_confidence=fake_conf
            )
            db.session.add(result)
            db.session.commit()
        else:
            # Mark anonymous use in session
            session['used_anonymous_classify'] = True
            result = ArticleResult(
                user_id=None,
                article_text=text,
                predicted_category=cat,
                fake_news_label=fake_label,
                category_confidence=cat_conf,
                fake_confidence=fake_conf
            )
            # Don't save anonymous results to DB
            db.session.rollback()

        return render_template('classify.html', result=result, is_anonymous=not is_authenticated)
    
    # Get user's classification history if logged in
    user_history = []
    if is_authenticated:
        user_history = ArticleResult.query.filter_by(user_id=current_user.id).order_by(ArticleResult.timestamp.desc()).all()
    
    # Show remaining uses message if not authenticated
    remaining_text = "You have 1 free classification remaining. Please login after to save results."
    return render_template('classify.html', remaining_text=remaining_text if not is_authenticated else None, user_history=user_history)


@classify_bp.route('/api_classify', methods=['POST'])
def api_classify_route():
    data = request.json or {}
    text = data.get('text')
    if not text:
        return jsonify({'error':'text required'}), 400
    cat, cat_conf = predict_category(text)
    fake_label, fake_conf = predict_fake_news(text)
    return jsonify({
        'category': cat,
        'category_confidence': cat_conf,
        'fake_news_label': fake_label,
        'fake_confidence': fake_conf
    })
