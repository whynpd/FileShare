import unittest
import json
from app import app, db
from models import User, UserRole

class AuthTestCase(unittest.TestCase):
    """Test case for authentication routes"""

    def setUp(self):
        """Set up test environment"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
            
            # Create test users
            ops_user = User(
                username='testops',
                email='testops@example.com',
                role=UserRole.OPERATIONS,
                is_verified=True
            )
            ops_user.set_password('password123')
            
            client_user = User(
                username='testclient',
                email='testclient@example.com',
                role=UserRole.CLIENT,
                is_verified=True
            )
            client_user.set_password('password123')
            
            unverified_user = User(
                username='unverified',
                email='unverified@example.com',
                role=UserRole.CLIENT,
                is_verified=False,
                verification_token='test-verification-token'
            )
            unverified_user.set_password('password123')
            
            db.session.add_all([ops_user, client_user, unverified_user])
            db.session.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_signup(self):
        """Test client user signup"""
        response = self.client.post(
            '/api/signup',
            data=json.dumps({
                'username': 'newuser',
                'email': 'newuser@example.com',
                'password': 'securepassword'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('verification_url', data)
        
        # Check user was created
        with app.app_context():
            user = User.query.filter_by(username='newuser').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.role, UserRole.CLIENT)
            self.assertFalse(user.is_verified)
    
    def test_login_operations_user(self):
        """Test operations user login"""
        response = self.client.post(
            '/api/login',
            data=json.dumps({
                'username': 'testops',
                'password': 'password123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('token', data)
        self.assertEqual(data['user']['role'], 'operations')
    
    def test_login_client_user(self):
        """Test client user login"""
        response = self.client.post(
            '/api/login',
            data=json.dumps({
                'username': 'testclient',
                'password': 'password123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('token', data)
        self.assertEqual(data['user']['role'], 'client')
    
    def test_login_unverified_user(self):
        """Test login with unverified user"""
        response = self.client.post(
            '/api/login',
            data=json.dumps({
                'username': 'unverified',
                'password': 'password123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('verify your email', data['message'].lower())
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post(
            '/api/login',
            data=json.dumps({
                'username': 'testclient',
                'password': 'wrongpassword'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_verify_email(self):
        """Test email verification"""
        response = self.client.get('/api/verify-email/test-verification-token')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'verified successfully', response.data)
        
        # Check user was verified
        with app.app_context():
            user = User.query.filter_by(username='unverified').first()
            self.assertTrue(user.is_verified)
            self.assertIsNone(user.verification_token)
    
    def test_verify_email_invalid_token(self):
        """Test email verification with invalid token"""
        response = self.client.get('/api/verify-email/invalid-token')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid verification token', response.data)

if __name__ == '__main__':
    unittest.main()
