import os
from flask import Blueprint, request, jsonify, send_file, current_app, url_for, session, redirect, render_template
from werkzeug.utils import secure_filename
from app import db
from models import File, UserRole, User
from utils import token_required, require_role, save_file, encrypt_url, validate_download_token

file_bp = Blueprint('file', __name__)

@file_bp.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload file (operations user only) - with support for both API and form-based requests"""
    # Check for session-based authentication
    user_id = session.get('user_id')
    role = session.get('role')
    
    # If session auth fails, try token auth
    if not user_id or role != UserRole.OPERATIONS.value:
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            # For form-based requests, redirect to login page
            if request.content_type and 'multipart/form-data' in request.content_type:
                return redirect('/login')
            return jsonify({'message': 'Authentication required!'}), 401
        
        # Extract token and verify
        token = auth_header.split(" ")[1]
        try:
            import jwt
            data = jwt.decode(
                token, 
                current_app.config['JWT_SECRET_KEY'], 
                algorithms=['HS256']
            )
            user = User.query.get(data['sub'])
            
            if not user or user.role != UserRole.OPERATIONS:
                return jsonify({'message': 'Permission denied!'}), 403
                
            current_user = user
        except Exception as e:
            # For form-based requests, redirect to login page with error
            if request.content_type and 'multipart/form-data' in request.content_type:
                return render_template('login.html', error='Invalid or expired token. Please login again.')
            return jsonify({'message': 'Invalid token!'}), 401
    else:
        # Use session authentication
        current_user = User.query.get(user_id)
        if not current_user or current_user.role != UserRole.OPERATIONS:
            return redirect('/login')
    
    # Check if file part exists in request
    if 'file' not in request.files:
        if request.content_type and 'multipart/form-data' in request.content_type:
            return render_template('upload.html', error='No file selected!')
        return jsonify({'message': 'No file part in the request!'}), 400
        
    file = request.files['file']
    
    # Check if a file was selected
    if file.filename == '':
        if request.content_type and 'multipart/form-data' in request.content_type:
            return render_template('upload.html', error='No file selected!')
        return jsonify({'message': 'No file selected!'}), 400
    
    # Save file to disk and database
    file_record, error = save_file(file, current_user.id)
    
    if error:
        if request.content_type and 'multipart/form-data' in request.content_type:
            return render_template('upload.html', error=f'Error saving file: {error}')
        return jsonify({'message': f'Error saving file: {error}'}), 500
    
    # Respond based on request type
    if request.content_type and 'multipart/form-data' in request.content_type:
        return render_template('upload.html', success=f'File {file.filename} uploaded successfully!')
        
    return jsonify({
        'message': 'File uploaded successfully!',
        'file': file_record.to_dict()
    }), 201

@file_bp.route('/api/files', methods=['GET'])
@token_required
@require_role([UserRole.CLIENT])
def list_files(current_user):
    """List all files (client user only)"""
    files = File.query.all()
    
    return jsonify({
        'files': [file.to_dict() for file in files]
    }), 200

@file_bp.route('/api/download-file/<int:file_id>', methods=['GET'])
@token_required
@require_role([UserRole.CLIENT])
def get_download_link(current_user, file_id):
    """Get encrypted download link for a file (client user only)"""
    # Check if file exists
    file = File.query.get(file_id)
    
    if not file:
        return jsonify({'message': 'File not found!'}), 404
    
    # Generate encrypted download URL
    encrypted_token, error = encrypt_url(file.id, current_user.id)
    
    if error:
        return jsonify({'message': f'Error generating download link: {error}'}), 500
    
    # Create download URL
    download_url = url_for('file.download_file', token=encrypted_token, _external=True)
    
    return jsonify({
        'download-link': download_url,
        'message': 'success'
    }), 200

@file_bp.route('/api/download/<token>', methods=['GET'])
@token_required
@require_role([UserRole.CLIENT])
def download_file(current_user, token):
    """Download file using encrypted token (client user only)"""
    file, error = validate_download_token(token, current_user.id)
    
    if error:
        return jsonify({'message': error}), 401
    
    # Check if file exists on disk
    if not os.path.exists(file.file_path):
        return jsonify({'message': 'File not found on the server!'}), 404
    
    # Send file
    return send_file(
        file.file_path,
        download_name=file.original_filename,
        as_attachment=True
    )

@file_bp.route('/api/files/<int:file_id>', methods=['GET'])
@token_required
def get_file_details(current_user, file_id):
    """Get file details"""
    file = File.query.get(file_id)
    
    if not file:
        return jsonify({'message': 'File not found!'}), 404
    
    return jsonify({
        'file': file.to_dict()
    }), 200

@file_bp.route('/api/files/<int:file_id>', methods=['DELETE'])
@token_required
@require_role([UserRole.OPERATIONS])
def delete_file(current_user, file_id):
    """Delete a file (operations user only)"""
    file = File.query.get(file_id)
    
    if not file:
        return jsonify({'message': 'File not found!'}), 404
    
    # Delete file from disk
    if os.path.exists(file.file_path):
        os.remove(file.file_path)
    
    # Delete file from database
    db.session.delete(file)
    
    try:
        db.session.commit()
        return jsonify({'message': 'File deleted successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting file: {str(e)}'}), 500
