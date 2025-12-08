from flask import Blueprint, render_template, request, redirect, url_for, flash
from .models import User
from .database import db
from .utils import hash_password, verify_password
from flask_login import login_user, logout_user, login_required

auth_bp = Blueprint('auth', __name__, template_folder='templates')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        user = User(name=name, email=email, password_hash=hash_password(password))
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if not user or not verify_password(user.password_hash, password):
            flash('Invalid credentials', 'danger')
            return redirect(url_for('auth.login'))
        login_user(user)
        flash('Logged in successfully', 'success')
        return redirect(url_for('index'))
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('auth.login'))
