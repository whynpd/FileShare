import unittest
import json
import os
import io
from app import app, db
from models import User, File, UserRole, DownloadToken
from utils import generate_token

class FileTestCase(unittest.TestCase):
    """Test case for file upload and download routes"""

    def setUp(self):
        """Set up test environment"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['UPLOAD_FOLDER'] = 'test_uploads'
        app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024  # 1MB for testing
        self.client = app.test_client()
        
        # Create test upload folder
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
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
            
            db.session.add_all([ops_user, client_user])
            db.session.commit()
            
            # Get user IDs
            self.ops_user_id = ops_user.id
            self.client_user_id = client_user.id
            
            # Generate tokens
            self.ops_token = generate_token(ops_user.id, ops_user.role)
            self.client_token = generate_token(client_user.id, client_user.role)
    
    def tearDown(self):
        """Clean up after tests"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
        
        # Clean up test files
        for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
            for file in files:
                os.remove(os.path.join(root, file))
        
        # Remove test folder
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            os.rmdir(app.config['UPLOAD_FOLDER'])
    
    def test_upload_file_operations_user(self):
        """Test file upload by operations user"""
        # Create a test file
        test_file = io.BytesIO(b'This is a test file content')
        test_filename = 'test_file.docx'
        
        # Send upload request
        response = self.client.post(
            '/api/upload',
            data={
                'file': (test_file, test_filename)
            },
            headers={
                'Authorization': f'Bearer {self.ops_token}'
            },
            content_type='multipart/form-data'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('file', data)
        self.assertEqual(data['file']['filename'], test_filename)
        
        # Check file was created in database
        with app.app_context():
            file = File.query.filter_by(original_filename=test_filename).first()
            self.assertIsNotNone(file)
            self.assertEqual(file.uploader_id, self.ops_user_id)
    
    def test_upload_file_client_user(self):
        """Test file upload by client user (should be denied)"""
        # Create a test file
        test_file = io.BytesIO(b'This is a test file content')
        test_filename = 'test_file.docx'
        
        # Send upload request
        response = self.client.post(
            '/api/upload',
            data={
                'file': (test_file, test_filename)
            },
            headers={
                'Authorization': f'Bearer {self.client_token}'
            },
            content_type='multipart/form-data'
        )
        
        self.assertEqual(response.status_code, 403)
    
    def test_upload_invalid_file_type(self):
        """Test uploading file with invalid extension"""
        # Create a test file
        test_file = io.BytesIO(b'This is a test file content')
        test_filename = 'test_file.txt'  # Not allowed
        
        # Send upload request
        response = self.client.post(
            '/api/upload',
            data={
                'file': (test_file, test_filename)
            },
            headers={
                'Authorization': f'Bearer {self.ops_token}'
            },
            content_type='multipart/form-data'
        )
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn('File type not allowed', data['message'])
    
    def test_list_files_client_user(self):
        """Test listing files by client user"""
        # First create a test file
        with app.app_context():
            file = File(
                filename='test_file_1.docx',
                original_filename='test_file_1.docx',
                file_path=os.path.join(app.config['UPLOAD_FOLDER'], 'test_file_1.docx'),
                file_type='docx',
                file_size=1024,
                uploader_id=self.ops_user_id
            )
            db.session.add(file)
            db.session.commit()
        
        # Send list files request
        response = self.client.get(
            '/api/files',
            headers={
                'Authorization': f'Bearer {self.client_token}'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('files', data)
        self.assertEqual(len(data['files']), 1)
        self.assertEqual(data['files'][0]['filename'], 'test_file_1.docx')
    
    def test_get_download_link(self):
        """Test getting download link for a file"""
        # First create a test file
        with app.app_context():
            file = File(
                filename='test_file_2.docx',
                original_filename='test_file_2.docx',
                file_path=os.path.join(app.config['UPLOAD_FOLDER'], 'test_file_2.docx'),
                file_type='docx',
                file_size=1024,
                uploader_id=self.ops_user_id
            )
            db.session.add(file)
            db.session.commit()
            file_id = file.id
        
        # Send download link request
        response = self.client.get(
            f'/api/download-file/{file_id}',
            headers={
                'Authorization': f'Bearer {self.client_token}'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('download-link', data)
        self.assertIn('success', data['message'])
        
        # Check download token was created
        with app.app_context():
            tokens = DownloadToken.query.filter_by(file_id=file_id, user_id=self.client_user_id).all()
            self.assertTrue(len(tokens) > 0)
    
    def test_get_download_link_operations_user(self):
        """Test getting download link as operations user (should be denied)"""
        # First create a test file
        with app.app_context():
            file = File(
                filename='test_file_3.docx',
                original_filename='test_file_3.docx',
                file_path=os.path.join(app.config['UPLOAD_FOLDER'], 'test_file_3.docx'),
                file_type='docx',
                file_size=1024,
                uploader_id=self.ops_user_id
            )
            db.session.add(file)
            db.session.commit()
            file_id = file.id
        
        # Send download link request
        response = self.client.get(
            f'/api/download-file/{file_id}',
            headers={
                'Authorization': f'Bearer {self.ops_token}'
            }
        )
        
        self.assertEqual(response.status_code, 403)

if __name__ == '__main__':
    unittest.main()
