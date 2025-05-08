import os
from flask import Blueprint, request, jsonify, send_file, current_app, url_for, session, redirect, render_template
from werkzeug.utils import secure_filename
from app import db
from models import File, UserRole, User
from utils import token_required, require_role, save_file, encrypt_url, validate_download_token

file_bp = Blueprint('file', __name__)

@file_bp.route('/api/upload', methods=['POST'])
@token_required
@require_role([UserRole.OPERATIONS])
def upload_file(current_user):
    """Upload file (operations user only)"""
    # Check if file part exists in request
    if 'file' not in request.files:
        return jsonify({'message': 'No file part in the request!'}), 400
        
    file = request.files['file']
    
    # Check if a file was selected
    if file.filename == '':
        return jsonify({'message': 'No file selected!'}), 400
    
    # Save file to disk and database
    file_record, error = save_file(file, current_user.id)
    
    if error:
        return jsonify({'message': f'Error saving file: {error}'}), 500
    
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
