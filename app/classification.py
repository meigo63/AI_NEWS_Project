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
from .utils import sanitize_text, allowed_file, explain_prediction  # أضفنا استدعاء explain_prediction

logger = logging.getLogger(__name__)

# حافظنا على اسم الـ Blueprint الأصلي الخاص بك
classify_bp = Blueprint('classify', __name__, template_folder='templates')

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')

# --- الكلاسات والدوال الأصلية (بدون تغيير لضمان استقرار السيستم) ---

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
            out = []
            for item in r:
                scores_list = item if isinstance(item, list) else [item]
                d = {}
                for s in scores_list:
                    if isinstance(s, dict):
                        d[s.get('label')] = float(s.get('score', 0.0))
                out.append(d)
            return out
        except Exception:
            return [{} for _ in texts]

def predict_category(text: str):
    models = current_app.config.get('ML_MODELS', {})
    model = models.get('classifier')
    if not model:
        return None, 0.0
    label_map = current_app.config.get('CATEGORY_LABEL_MAP', {
        'LABEL_0': 'ArtsAndCulture', 'LABEL_1': 'Business', 'LABEL_2': 'Entertainment',
        'LABEL_3': 'GeneralNews', 'LABEL_4': 'Health', 'LABEL_5': 'Other',
        'LABEL_6': 'Politics', 'LABEL_7': 'Sports', 'LABEL_8': 'Technology',
    })
    try:
        if hasattr(model, 'pipeline'):
            try:
                res = model.pipeline(text, return_all_scores=True)
            except TypeError:
                res = model.pipeline(text)
            if isinstance(res, list) and len(res) > 0:
                scores = res[0] if isinstance(res[0], list) else res
                if isinstance(scores, list) and scores and isinstance(scores[0], dict):
                    best = max(scores, key=lambda x: x.get('score', 0.0))
                    raw_lbl = best.get('label', '')
                    sc = float(best.get('score', 0.0))
                    mapped = label_map.get(str(raw_lbl), str(raw_lbl))
                    return mapped, sc
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

def predict_fake_news(text: str):
    models = current_app.config.get('ML_MODELS', {})
    model = models.get('fake')
    if not model:
        return None, 0.0
    label_map = current_app.config.get('FAKE_LABEL_MAP', {'LABEL_0': 'real', 'LABEL_1': 'fake'})
    try:
        if hasattr(model, 'pipeline'):
            try:
                res = model.pipeline(text, return_all_scores=True)
            except TypeError:
                res = model.pipeline(text)
            if isinstance(res, list) and len(res) > 0:
                scores = res[0] if isinstance(res[0], list) else res
                if isinstance(scores, list) and scores and isinstance(scores[0], dict):
                    best = max(scores, key=lambda x: x.get('score', 0.0))
                    raw_lbl = best.get('label', '')
                    sc = float(best.get('score', 0.0))
                    mapped = label_map.get(str(raw_lbl))
                    if mapped: return mapped, sc
        out = model.predict([text])
        if isinstance(out, list) and out:
            lbl_raw = out[0]
            sc = float(lbl_raw.get('score', 0.0)) if isinstance(lbl_raw, dict) else 0.0
            raw_lbl = lbl_raw.get('label', '') if isinstance(lbl_raw, dict) else lbl_raw
            mapped = label_map.get(str(raw_lbl))
            if mapped: return mapped, sc
    except Exception:
        logger.exception('predict_fake_news failed')
    return None, 0.0

# --- الدالة الرئيسية المعدلة لإضافة LIME ---

@classify_bp.route('/classify', methods=['GET', 'POST'])
def classify_page():
    is_authenticated = current_user.is_authenticated
    free_uses = session.get('free_uses', 0)
    max_free = 3
    result = None
    explanation_html = None  # متغير لتخزين رسم LIME

    if request.method == 'POST':
        if not is_authenticated and free_uses >= max_free:
            flash('Free classification limit reached. Please register or login.', 'info')
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

        # 1. تنفيذ التصنيف الأصلي
        cat, cat_conf = predict_category(text)
        fake_label, fake_conf = predict_fake_news(text)
        
        # 2. إنشاء كائن النتيجة
        result = ArticleResult(
            user_id=current_user.id if is_authenticated else None,
            article_text=text,
            predicted_category=cat,
            fake_news_label=(fake_label if fake_label in ('real', 'fake') else None),
            category_confidence=cat_conf,
            fake_confidence=fake_conf,
        )

        # 3. حفظ البيانات (حذفنا جزء حساب LIME من هنا لزيادة السرعة)
        if is_authenticated:
            db.session.add(result)
            db.session.commit()
        else:
            session['free_uses'] = free_uses + 1

        # نرسل فقط الـ result (الشرح سيطلب لاحقاً عبر AJAX)
        return render_template('classify.html', 
                               result=result, 
                               is_anonymous=not is_authenticated)
        
        
    # عرض التاريخ في حالة الـ GET
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
    
    
    
@classify_bp.route('/get_explanation', methods=['POST'])
@login_required
def get_explanation():
    """
    مسار خاص لاستدعاء تحليل LIME عند طلب المستخدم (للمسجلين فقط).
    """
    data = request.json or {}
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    # الوصول للموديلات المخزنة في الإعدادات
    models = current_app.config.get('ML_MODELS', {})
    fake_model_wrapper = models.get('fake')
    
    if fake_model_wrapper:
        try:
            # استدعاء دالة الشرح من utils.py
            explanation_html, top_words = explain_prediction(text, fake_model_wrapper)
            
            # في حال فشل LIME في إنتاج نتيجة
            if not explanation_html:
                return jsonify({'error': 'Could not generate explanation at this moment.'}), 500

            return jsonify({
                'explanation_html': explanation_html,
                'top_words': top_words
            })
        except Exception as e:
            logger.exception("Error during LIME explanation generation")
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Prediction model not available'}), 500