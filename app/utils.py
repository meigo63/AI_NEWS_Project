from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import request, jsonify
from .models import User

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
