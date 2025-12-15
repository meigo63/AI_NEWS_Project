import os
import pickle
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from .models import ArticleResult
from .database import db
from flask_login import current_user
from .utils import sanitize_text, allowed_file
from flask_login import login_required
import logging

logger = logging.getLogger(__name__)

classify_bp = Blueprint('classify', __name__, template_folder='templates')


# per-request helpers will use app.config['ML_MODELS'] if present


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
    models = current_app.config.get('ML_MODELS', {})
    model = models.get('classifier')
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
    models = current_app.config.get('ML_MODELS', {})
    model = models.get('fake')
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
    is_authenticated = current_user.is_authenticated
    free_uses = session.get('free_uses', 0)
    max_free = 3

    if request.method == 'POST':
        # enforce free limit for anonymous users
        if not is_authenticated and free_uses >= max_free:
            flash('Free classification limit reached. Please register or login to continue.', 'info')
            return redirect(url_for('auth.login'))

        # text input or file upload
        text = ''
        if 'file' in request.files and request.files['file'].filename:
            f = request.files['file']
            if not allowed_file(f.filename):
                flash('Invalid file type. Only .txt allowed.', 'danger')
                return redirect(url_for('classify.classify_page'))
            try:
                raw = f.read().decode('utf-8', errors='ignore')
                text = sanitize_text(raw)
            except Exception:
                flash('Could not read uploaded file', 'danger')
                return redirect(url_for('classify.classify_page'))
        else:
            text = sanitize_text(request.form.get('article_text', ''))

        if not text:
            flash('Empty input provided', 'warning')
            return redirect(url_for('classify.classify_page'))

        cat, cat_conf = predict_category(text)
        fake_label, fake_conf = predict_fake_news(text)
        logger.info('Classification requested user=%s anonymous=%s', current_user.get_id() if current_user.is_authenticated else None, not current_user.is_authenticated)

        result = ArticleResult(
            user_id=current_user.id if is_authenticated else None,
            article_text=text,
            predicted_category=cat,
            fake_news_label=(fake_label if fake_label in ('real', 'fake') else fake_label),
            category_confidence=cat_conf,
            fake_confidence=fake_conf,
        )

        if is_authenticated:
            db.session.add(result)
            db.session.commit()
        else:
            # increment free uses and do not persist
            session['free_uses'] = free_uses + 1

        return render_template('classify.html', result=result, is_anonymous=not is_authenticated)

    # GET
    user_history = []
    if is_authenticated:
        user_history = ArticleResult.query.filter_by(user_id=current_user.id).order_by(ArticleResult.timestamp.desc()).all()

    remaining = None
    if not is_authenticated:
        remaining = max(0, 3 - session.get('free_uses', 0))

    return render_template('classify.html', remaining=remaining, user_history=user_history)


@classify_bp.route('/history')
@login_required
def history_page():
    user_history = ArticleResult.query.filter_by(user_id=current_user.id).order_by(ArticleResult.timestamp.desc()).all()
    return render_template('history.html', user_history=user_history)


@classify_bp.route('/api_classify', methods=['POST'])
def api_classify_route():
    data = request.json or {}
    text = data.get('text')
    if not text:
        return jsonify({'error': 'text required'}), 400
    text = sanitize_text(text)
    cat, cat_conf = predict_category(text)
    fake_label, fake_conf = predict_fake_news(text)
    return jsonify({
        'category': cat,
        'category_confidence': float(cat_conf or 0.0),
        'fake_news_label': (fake_label if fake_label in ('real', 'fake') else None),
        'fake_confidence': float(fake_conf or 0.0),
    })
