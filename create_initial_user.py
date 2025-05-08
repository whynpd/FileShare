from app import app, db
from models import User, UserRole

# Script to create initial operations user for testing

def create_ops_user():
    with app.app_context():
        # Check if user already exists
        if User.query.filter_by(username='admin').first():
            print("Operations user 'admin' already exists")
            return
        
        # Create operations user
        ops_user = User(
            username='admin',
            email='admin@example.com',
            role=UserRole.OPERATIONS,
            is_verified=True
        )
        ops_user.set_password('admin123')
        
        # Add to database
        db.session.add(ops_user)
        db.session.commit()
        print("Created operations user:")
        print("Username: admin")
        print("Password: admin123")
        print("Role: Operations")

if __name__ == '__main__':
    create_ops_user()