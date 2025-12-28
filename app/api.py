from flask import Blueprint, request, jsonify
from .models import User, ArticleResult
from .database import db
from .utils import token_auth_required, verify_password
from .classification import predict_category, predict_fake_news
from .models import Feedback

api_bp = Blueprint('api', __name__)

@api_bp.route('/login', methods=['POST'])
def api_login():
    data = request.json or {}
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error':'email and password required'}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error':'invalid credentials'}), 401
    if not verify_password(user.password_hash, password):
        return jsonify({'error':'invalid credentials'}), 401
    token = user.generate_token()
    db.session.commit()
    return jsonify({'token': token, 'role': user.role})

@api_bp.route('/classify', methods=['POST'])
@token_auth_required
def api_classify():
    data = request.json or {}
    text = data.get('text')
    if not text:
        return jsonify({'error':'text required'}), 400
    category, cat_conf = predict_category(text)
    fake_label, fake_conf = predict_fake_news(text)

    user = request.user
    result = ArticleResult(
        user_id=user.id,
        article_text=text,
        predicted_category=category,
        fake_news_label=fake_label,
        category_confidence=cat_conf,
        fake_confidence=fake_conf
    )
    db.session.add(result)
    db.session.commit()

    return jsonify({
        'category': category if category is not None else None,
        'category_confidence': float(cat_conf or 0.0),
        'fake_news_label': (fake_label if fake_label in ('real','fake') else None),
        'fake_confidence': float(fake_conf or 0.0)
    })

@api_bp.route('/history', methods=['GET'])
@token_auth_required
def api_history():
    user = request.user
    items = ArticleResult.query.filter_by(user_id=user.id).order_by(ArticleResult.timestamp.desc()).all()
    out = []
    for r in items:
        out.append({
            'article_text': r.article_text,
            'predicted_category': r.predicted_category,
            'category_confidence': r.category_confidence,
            'fake_news_label': r.fake_news_label,
            'fake_confidence': r.fake_confidence,
            'timestamp': r.timestamp.isoformat()
        })
    return jsonify(out)

@api_bp.route('/admin/users', methods=['GET'])
@token_auth_required
def api_admin_users():
    user = request.user
    if user.role != 'admin':
        return jsonify({'error':'admin only'}), 403
    users = User.query.all()
    out = [{'id':u.id,'name':u.name,'email':u.email,'role':u.role,'created_at':u.created_at.isoformat()} for u in users]
    return jsonify(out)

@api_bp.route('/admin/results', methods=['GET'])
@token_auth_required
def api_admin_results():
    user = request.user
    if user.role != 'admin':
        return jsonify({'error':'admin only'}), 403
    results = ArticleResult.query.order_by(ArticleResult.timestamp.desc()).all()
    out = []
    for r in results:
        out.append({
            'id': r.id,
            'user_id': r.user_id,
            'article_text': r.article_text,
            'predicted_category': r.predicted_category,
            'fake_news_label': r.fake_news_label,
            'category_confidence': r.category_confidence,
            'fake_confidence': r.fake_confidence,
            'timestamp': r.timestamp.isoformat()
        })
    return jsonify(out)


@api_bp.route('/admin/feedback', methods=['GET'])
@token_auth_required
def api_admin_feedback():
    user = request.user
    if user.role != 'admin':
        return jsonify({'error': 'admin only'}), 403
    items = Feedback.query.order_by(Feedback.timestamp.desc()).all()
    out = []
    for f in items:
        out.append({'id': f.id, 'user_id': f.user_id, 'feedback_text': f.feedback_text, 'timestamp': f.timestamp.isoformat()})
    return jsonify(out)
