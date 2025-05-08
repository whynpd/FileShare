import secrets
import datetime
from flask import Blueprint, request, jsonify, url_for, current_app, render_template, session, redirect
from werkzeug.security import generate_password_hash
from app import db
from models import User, UserRole
from utils import generate_token, token_required, send_verification_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/signup', methods=['POST'])
def signup():
    """API route for client user signup"""
    data = request.get_json()
    
    # Validate required fields
    if not all(k in data for k in ('username', 'email', 'password')):
        return jsonify({'message': 'Missing required fields!'}), 400
    
    # Check if user already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already exists!'}), 400
        
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already exists!'}), 400
    
    # Create verification token
    verification_token = secrets.token_urlsafe(32)
    
    # Create new user (client role only for signup)
    new_user = User(
        username=data['username'],
        email=data['email'],
        role=UserRole.CLIENT,
        is_verified=False,
        verification_token=verification_token
    )
    new_user.set_password(data['password'])
    
    # Add to database
    db.session.add(new_user)
    
    try:
        db.session.commit()
        
        # Generate verification URL
        verification_url = url_for(
            'auth.verify_email',
            token=verification_token,
            _external=True
        )
        
        # Send verification email
        success, error = send_verification_email(new_user, verification_url)
        
        if not success:
            current_app.logger.error(f"Failed to send verification email: {error}")
            return jsonify({
                'message': 'User created but failed to send verification email. Please contact support.',
                'verification_url': verification_url  # Include URL in response for testing
            }), 201
        
        return jsonify({
            'message': 'User created successfully! Please check your email to verify your account.',
            'verification_url': verification_url  # Include URL in response for testing
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating user: {str(e)}'}), 500

@auth_bp.route('/api/verify-email/<token>', methods=['GET'])
def verify_email(token):
    """Verify user email with token"""
    user = User.query.filter_by(verification_token=token).first()
    
    if not user:
        return render_template('email_verification.html', success=False, 
                               message="Invalid verification token!")
    
    # Update user verification status
    user.is_verified = True
    user.verification_token = None
    
    try:
        db.session.commit()
        return render_template('email_verification.html', success=True, 
                               message="Email verified successfully! You can now log in.")
    except Exception as e:
        db.session.rollback()
        return render_template('email_verification.html', success=False, 
                               message=f"Error verifying email: {str(e)}")

@auth_bp.route('/api/login', methods=['POST'])
def login():
    """API route for user login (both client and operations users)"""
    # Check if this is a form submission or an API call
    if request.content_type and 'application/json' in request.content_type:
        # API JSON request
        data = request.get_json()
        
        # Validate required fields
        if not all(k in data for k in ('username', 'password')):
            return jsonify({'message': 'Missing username or password!'}), 400
        
        username = data['username']
        password = data['password']
        is_api = True
    else:
        # Form submission
        username = request.form.get('username')
        password = request.form.get('password')
        is_api = False
        
        if not username or not password:
            if is_api:
                return jsonify({'message': 'Missing username or password!'}), 400
            else:
                return render_template('login.html', error='Username and password are required')
    
    # Find user
    user = User.query.filter_by(username=username).first()
    
    if not user:
        if is_api:
            return jsonify({'message': 'Invalid username or password!'}), 401
        else:
            return render_template('login.html', error='Invalid username or password')
    
    # Check password
    if not user.check_password(password):
        if is_api:
            return jsonify({'message': 'Invalid username or password!'}), 401
        else:
            return render_template('login.html', error='Invalid username or password')
    
    # Check if client user is verified
    if user.role == UserRole.CLIENT and not user.is_verified:
        if is_api:
            return jsonify({'message': 'Please verify your email before logging in!'}), 401
        else:
            return render_template('login.html', error='Please verify your email before logging in')
    
    # Generate token
    token = generate_token(user.id, user.role)
    
    # Store user info in session for server-side auth
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role.value
    
    if is_api:
        return jsonify({
            'message': 'Login successful!',
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role.value
            }
        }), 200
    else:
        # Redirect based on role
        if user.role == UserRole.OPERATIONS:
            return redirect('/upload')
        else:
            return redirect('/files')

@auth_bp.route('/api/create-ops-user', methods=['POST'])
@token_required
def create_ops_user(current_user):
    """API route to create operations user (admin only)"""
    # This endpoint would typically be restricted to admin users
    # For simplicity, we'll allow any authenticated user to create an ops user
    
    data = request.get_json()
    
    # Validate required fields
    if not all(k in data for k in ('username', 'email', 'password')):
        return jsonify({'message': 'Missing required fields!'}), 400
    
    # Check if user already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already exists!'}), 400
        
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already exists!'}), 400
    
    # Create new operations user
    new_user = User(
        username=data['username'],
        email=data['email'],
        role=UserRole.OPERATIONS,
        is_verified=True  # Operations users don't need email verification
    )
    new_user.set_password(data['password'])
    
    # Add to database
    db.session.add(new_user)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Operations user created successfully!'}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating user: {str(e)}'}), 500

@auth_bp.route('/api/user/profile', methods=['GET'])
@token_required
def get_user_profile(current_user):
    """Get current user profile"""
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'role': current_user.role.value,
        'is_verified': current_user.is_verified,
        'created_at': current_user.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }), 200
