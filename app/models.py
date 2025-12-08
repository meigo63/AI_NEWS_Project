from datetime import datetime
from .database import db
from flask_login import UserMixin
import uuid

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'user', name='user_roles'), default='user', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    api_token = db.Column(db.String(64), unique=True, nullable=True)

    results = db.relationship('ArticleResult', backref='user', lazy=True)

    def generate_token(self):
        self.api_token = uuid.uuid4().hex
        return self.api_token

class ArticleResult(db.Model):
    __tablename__ = 'article_results'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    article_text = db.Column(db.Text, nullable=False)
    predicted_category = db.Column(db.String(128), nullable=True)
    fake_news_label = db.Column(db.String(16), nullable=True)
    category_confidence = db.Column(db.Float, nullable=True)
    fake_confidence = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
