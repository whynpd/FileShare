import datetime
import enum
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class UserRole(enum.Enum):
    OPERATIONS = 'operations'
    CLIENT = 'client'

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    files = db.relationship('File', backref='uploader', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_operations_user(self):
        return self.role == UserRole.OPERATIONS
    
    def is_client_user(self):
        return self.role == UserRole.CLIENT

class File(db.Model):
    __tablename__ = 'files'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.original_filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'uploader': self.uploader.username,
            'uploaded_at': self.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class DownloadToken(db.Model):
    __tablename__ = 'download_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(512), nullable=False, unique=True)
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    expiration = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    
    # Relationships
    file = db.relationship('File', backref='download_tokens')
    user = db.relationship('User', backref='download_tokens')
    
    def is_expired(self):
        return datetime.datetime.utcnow() > self.expiration
