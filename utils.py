import os
import secrets
import datetime
import uuid
from functools import wraps
from flask import jsonify, request, current_app
import jwt
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
from flask_mail import Message
from app import mail, db
from models import User, UserRole, DownloadToken

# Authentication utilities
def generate_token(user_id, role, expiry=None):
    """Generate a JWT token for authentication"""
    if expiry is None:
        expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        
    payload = {
        'exp': expiry,
        'iat': datetime.datetime.utcnow(),
        'sub': user_id,
        'role': role.value
    }
    
    return jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )

def token_required(f):
    """Decorator for routes that require a valid token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]
            
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
            
        try:
            data = jwt.decode(
                token, 
                current_app.config['JWT_SECRET_KEY'], 
                algorithms=['HS256']
            )
            current_user = User.query.get(data['sub'])
            
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401
            
        return f(current_user, *args, **kwargs)
        
    return decorated

def require_role(roles):
    """Decorator to check if user has required role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(current_user, *args, **kwargs):
            if current_user.role not in roles:
                return jsonify({'message': 'Permission denied!'}), 403
            return f(current_user, *args, **kwargs)
        return decorated_function
    return decorator

# File utilities
def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_file(file, uploader_id):
    """Save uploaded file to filesystem and database"""
    if not allowed_file(file.filename):
        return None, "File type not allowed"
    
    # Create upload folder if it doesn't exist
    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Generate secure filename
    original_filename = file.filename
    filename = secure_filename(file.filename)
    file_extension = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    
    # Save file to disk
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)
    
    # Create file record in database
    from models import File
    file_size = os.path.getsize(file_path)
    file_record = File(
        filename=unique_filename,
        original_filename=original_filename,
        file_path=file_path,
        file_type=file_extension,
        file_size=file_size,
        uploader_id=uploader_id
    )
    
    try:
        db.session.add(file_record)
        db.session.commit()
        return file_record, None
    except Exception as e:
        db.session.rollback()
        # Delete the file if database operation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        return None, str(e)

# URL encryption utilities
def get_encryption_key():
    """Get or generate Fernet encryption key"""
    key = current_app.config.get('ENCRYPTION_KEY')
    if not key:
        # Generate a key and store it in the app config
        key = Fernet.generate_key()
        current_app.config['ENCRYPTION_KEY'] = key
    return key

def encrypt_url(file_id, user_id):
    """Generate encrypted download token for a file"""
    # Create a download token
    token = secrets.token_urlsafe(32)
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    
    download_token = DownloadToken(
        token=token,
        file_id=file_id,
        user_id=user_id,
        expiration=expiration
    )
    
    try:
        db.session.add(download_token)
        db.session.commit()
        
        # Return the encrypted token
        encrypted_token = token
        return encrypted_token, None
    except Exception as e:
        db.session.rollback()
        return None, str(e)

def validate_download_token(token, user_id):
    """Validate a download token"""
    download_token = DownloadToken.query.filter_by(token=token, is_used=False).first()
    
    if not download_token:
        return None, "Invalid or used download token"
        
    if download_token.is_expired():
        return None, "Download token has expired"
        
    if download_token.user_id != user_id:
        return None, "You are not authorized to use this download token"
    
    # Mark token as used
    download_token.is_used = True
    db.session.commit()
    
    return download_token.file, None

# Email utilities
def send_verification_email(user, verification_url):
    """Send email verification email"""
    msg = Message(
        subject="Verify Your Email Address",
        recipients=[user.email],
        html=f"""
        <h1>Email Verification</h1>
        <p>Hi {user.username},</p>
        <p>Thank you for registering. Please click the link below to verify your email address:</p>
        <p><a href="{verification_url}">Verify Email</a></p>
        <p>This link will expire in 24 hours.</p>
        <p>If you did not create an account, please ignore this email.</p>
        """
    )
    
    try:
        mail.send(msg)
        return True, None
    except Exception as e:
        return False, str(e)
