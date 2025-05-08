import os

class Config:
    # Flask configuration
    DEBUG = True
    
    # SQLAlchemy configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')
    
    # Upload configuration
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    ALLOWED_EXTENSIONS = {'pptx', 'docx', 'xlsx'}
    
    # JWT configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'default-jwt-secret-key')
    JWT_TOKEN_LOCATION = ['headers']
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
