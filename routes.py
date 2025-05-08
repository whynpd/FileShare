from flask import Blueprint, render_template, redirect, url_for, request
from flask import current_app as app

# Create blueprint for web routes
web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    """Render the home page"""
    return render_template('dashboard.html')

@web_bp.route('/login')
def login():
    """Render the login page"""
    return render_template('login.html')

@web_bp.route('/signup')
def signup():
    """Render the signup page"""
    return render_template('signup.html')

@web_bp.route('/files')
def files():
    """Render the files page for client users"""
    return render_template('files.html')

@web_bp.route('/upload')
def upload():
    """Render the upload page for operations users"""
    return render_template('upload.html')

@web_bp.route('/profile')
def profile():
    """Render the user profile page"""
    # This would typically be protected and use the current user data
    return render_template('dashboard.html')