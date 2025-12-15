from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .models import User
from .database import db
from .utils import sanitize_text
from flask_login import login_user, logout_user, login_required
from .models import Feedback
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, template_folder='templates')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = sanitize_text(request.form.get('name', ''))
        email = sanitize_text(request.form.get('email', ''))
        password = request.form.get('password', '')
        if not name or not email or not password:
            flash('All fields are required', 'danger')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        user = User(name=name, email=email)
        user.set_password(password)
        user.generate_token()
        db.session.add(user)
        db.session.commit()
        login_user(user)
        session['user_id'] = user.id
        # Reset guest free usage on register
        session['free_uses'] = 0
        logger.info('New user registered: %s', user.email)
        flash('Registration successful. You are logged in.', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = sanitize_text(request.form.get('email', ''))
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            logger.warning('Failed login attempt for: %s', email)
            flash('Invalid credentials', 'danger')
            return redirect(url_for('auth.login'))
        # ensure API token
        if not user.api_token:
            user.generate_token()
            db.session.commit()
        login_user(user)
        session['user_id'] = user.id
        session['free_uses'] = 0
        logger.info('User logged in: %s', user.email)
        flash('Logged in successfully', 'success')
        return redirect(url_for('index'))
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('user_id', None)
    flash('Logged out', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/feedback', methods=['GET', 'POST'])
@login_required
def submit_feedback():
    if request.method == 'POST':
        text = sanitize_text(request.form.get('feedback_text', '').strip())
        if not text:
            flash('Feedback cannot be empty', 'warning')
            return redirect(url_for('auth.submit_feedback'))
        fb = Feedback(user_id=session.get('user_id'), feedback_text=text)
        db.session.add(fb)
        db.session.commit()
        logger.info('Feedback submitted by user_id=%s', session.get('user_id'))
        flash('Thank you for your feedback', 'success')
        return redirect(url_for('index'))
    return render_template('feedback.html')
