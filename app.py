import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_mail import Mail
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Define base for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
mail = Mail()

# Create the Flask app
app = Flask(__name__)

# Load configuration
app.config.from_object('config.Config')

# Set secret key
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key-for-development")

# Configure ProxyFix for proper URL generation
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize extensions with the app
db.init_app(app)
mail.init_app(app)

# Create database tables
with app.app_context():
    # Import models here to avoid circular imports
    import models  # noqa: F401
    db.create_all()

# Register routes
from auth_routes import auth_bp
from file_routes import file_bp
from routes import web_bp

app.register_blueprint(auth_bp)
app.register_blueprint(file_bp)
app.register_blueprint(web_bp)

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return {"error": "Resource not found"}, 404

@app.errorhandler(500)
def internal_server_error(e):
    return {"error": "Internal server error"}, 500
