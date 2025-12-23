import os
import pickle
import logging
from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    flash,
    current_app,
)
from .models import ArticleResult
from .database import db
from flask_login import current_user, login_required
from .utils import sanitize_text, allowed_file

logger = logging.getLogger(__name__)

classify_bp = Blueprint('classify', __name__, template_folder='templates')

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')


class SimpleWrapper:
    """Small wrapper to normalize model interface used by this app."""

    def __init__(self, pipeline=None):
        self.pipeline = pipeline

    def predict(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        out = []
        for t in texts:
            try:
                r = self.pipeline(t)
                # pipeline often returns list[{'label':..., 'score':...}]
                if isinstance(r, list) and len(r) > 0:
                    first = r[0]
                    if isinstance(first, dict) and 'label' in first:
                        out.append(first['label'])
                    else:
                        out.append(first)
                elif isinstance(r, dict) and 'label' in r:
                    out.append(r['label'])
                else:
                    out.append(r)
            except Exception:
                out.append(None)
        return out

    def predict_proba(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        try:
            r = self.pipeline(texts, return_all_scores=True)
            # r can be list[list[{label, score}]] or list[{label, score}]
            out = []
            for item in r:
                scores_list = item if isinstance(item, list) else [item]
                # convert list of dicts to dict label->score
                d = {}
                for s in scores_list:
                    if isinstance(s, dict):
                        d[s.get('label')] = float(s.get('score', 0.0))
                out.append(d)
            return out
        except Exception:
            # fallback: return empty dicts
            return [{} for _ in texts]


def predict_category(text: str):
    models = current_app.config.get('ML_MODELS', {})
    model = models.get('classifier')
    if not model:
        return None, 0.0

    # allow override via config; default mapping for typical 9-class news categorization
    label_map = current_app.config.get('CATEGORY_LABEL_MAP', {
        'LABEL_0': 'ArtsAndCulture',
        'LABEL_1': 'Business',
        'LABEL_2': 'Entertainment',
        'LABEL_3': 'GeneralNews',
        'LABEL_4': 'Health',
        'LABEL_5': 'Other',
        'LABEL_6': 'Politics',
        'LABEL_7': 'Sports',
        'LABEL_8': 'Technology',
    })

    try:
        # try score-based output
        if hasattr(model, 'pipeline'):
            try:
                res = model.pipeline(text, return_all_scores=True)
            except TypeError:
                res = model.pipeline(text)
            logger.info('Category raw output: %s', res)
            if isinstance(res, list) and len(res) > 0:
                scores = res[0] if isinstance(res[0], list) else res
                if isinstance(scores, list) and scores and isinstance(scores[0], dict):
                    best = max(scores, key=lambda x: x.get('score', 0.0))
                    raw_lbl = best.get('label', '')
                    sc = float(best.get('score', 0.0))
                    mapped = label_map.get(str(raw_lbl), str(raw_lbl))
                    return mapped, sc
        # fallback to wrapper
        out = model.predict([text])
        if out and isinstance(out, list):
            val = out[0]
            if isinstance(val, dict):
                raw_lbl = val.get('label', '')
                mapped = label_map.get(str(raw_lbl), str(raw_lbl))
                return mapped, float(val.get('score', 0.0))
            mapped = label_map.get(str(val), str(val))
            return mapped, 0.0
    except Exception:
        logger.exception('predict_category failed')
    return None, 0.0


def category_topk(text: str, k: int = 5):
    """Return top-k mapped categories with scores as list of dicts."""
    models = current_app.config.get('ML_MODELS', {})
    model = models.get('classifier')
    if not model:
        return []

    label_map = current_app.config.get('CATEGORY_LABEL_MAP', {})
    try:
        # prefer pipeline with top_k / return_all_scores
        if hasattr(model, 'pipeline'):
            try:
                res = model.pipeline(text, return_all_scores=True)
            except TypeError:
                # newer transformers prefer top_k=None
                try:
                    res = model.pipeline(text, top_k=None)
                except Exception:
                    res = model.pipeline(text)

            logger.info('Category raw output (topk): %s', res)
            if isinstance(res, list) and len(res) > 0:
                scores = res[0] if isinstance(res[0], list) else res
                if isinstance(scores, list):
                    mapped = []
                    for item in sorted(scores, key=lambda x: x.get('score', 0.0), reverse=True)[:k]:
                        raw_lbl = item.get('label')
                        mapped_label = label_map.get(str(raw_lbl), str(raw_lbl))
                        mapped.append({'label': mapped_label, 'score': float(item.get('score', 0.0))})
                    return mapped

        # fallback: try wrapper predict_proba
        if hasattr(model, 'predict_proba'):
            probs = model.predict_proba([text])
            if isinstance(probs, list) and probs:
                d = probs[0]
                items = sorted(d.items(), key=lambda x: x[1], reverse=True)[:k]
                return [{'label': label_map.get(str(lbl), str(lbl)), 'score': float(s)} for lbl, s in items]
    except Exception:
        logger.exception('category_topk failed')
    return []


def predict_fake_news(text: str):
    models = current_app.config.get('ML_MODELS', {})
    model = models.get('fake')
    if not model:
        return None, 0.0

    # allow override via config; default mapping observed in tests
    label_map = current_app.config.get('FAKE_LABEL_MAP', {'LABEL_0': 'real', 'LABEL_1': 'fake'})

    try:
        if hasattr(model, 'pipeline'):
            try:
                res = model.pipeline(text, return_all_scores=True)
            except TypeError:
                res = model.pipeline(text)
            logger.info('Fake model raw output: %s', res)
            if isinstance(res, list) and len(res) > 0:
                scores = res[0] if isinstance(res[0], list) else res
                if isinstance(scores, list) and scores and isinstance(scores[0], dict):
                    best = max(scores, key=lambda x: x.get('score', 0.0))
                    raw_lbl = best.get('label', '')
                    lbl = str(raw_lbl)
                    sc = float(best.get('score', 0.0))
                    mapped = label_map.get(lbl)
                    if mapped:
                        return mapped, sc
                    if 'fake' in lbl.lower():
                        return 'fake', sc
                    if 'real' in lbl.lower():
                        return 'real', sc

        out = model.predict([text])
        logger.info('Fake model predict output: %s', out)
        if isinstance(out, list) and out:
            lbl_raw = out[0]
            if isinstance(lbl_raw, dict):
                raw_lbl = lbl_raw.get('label', '')
                sc = float(lbl_raw.get('score', 0.0))
            else:
                raw_lbl = lbl_raw
                sc = 0.0
            mapped = label_map.get(str(raw_lbl))
            if mapped:
                return mapped, sc
            lbl = str(raw_lbl).lower()
            if 'fake' in lbl:
                return 'fake', sc
            if 'real' in lbl:
                return 'real', sc

        # final fallback: inspect classes_ and label_map
        classes = getattr(model, 'classes_', None)
        if classes:
            for c in classes:
                mapped = label_map.get(c)
                if mapped:
                    return mapped, 0.0
                if isinstance(c, str) and 'fake' in c.lower():
                    return 'fake', 0.0
                if isinstance(c, str) and 'real' in c.lower():
                    return 'real', 0.0
    except Exception:
        logger.exception('predict_fake_news failed')
    return None, 0.0


@classify_bp.route('/classify', methods=['GET', 'POST'])
def classify_page():
    is_authenticated = current_user.is_authenticated
    free_uses = session.get('free_uses', 0)
    max_free = 3

    if request.method == 'POST':
        if not is_authenticated and free_uses >= max_free:
            flash('Free classification limit reached. Please register or login to continue.', 'info')
            return redirect(url_for('auth.login'))

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
            fake_news_label=(fake_label if fake_label in ('real', 'fake') else None),
            category_confidence=cat_conf,
            fake_confidence=fake_conf,
        )

        if is_authenticated:
            db.session.add(result)
            db.session.commit()
        else:
            session['free_uses'] = free_uses + 1

        return render_template('classify.html', result=result, is_anonymous=not is_authenticated)

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
    topk = category_topk(text, k=5)
    return jsonify({
        'category': cat,
        'category_confidence': float(cat_conf or 0.0),
        'category_top': topk,
        'fake_news_label': (fake_label if fake_label in ('real', 'fake') else None),
        'fake_confidence': float(fake_conf or 0.0),
    })
