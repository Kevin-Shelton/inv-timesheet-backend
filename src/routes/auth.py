from flask import Blueprint, request, jsonify, g
import bcrypt
from src.utils.supabase import get_supabase_client, get_supabase_admin_client
from src.utils.jwt_utils import create_access_token
from src.middleware.auth import token_required, log_activity
from src.utils.email_utils import send_welcome_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login endpoint
    
    Request body:
        {
            "email": "user@example.com",
            "password": "password123"
        }
        
    Returns:
        JWT token and user information
    """
    data = request.json
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Email and password are required'}), 400
        
    email = data.get('email')
    password = data.get('password')
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Query user by email
    response = supabase.table('users').select('*').eq('email', email).execute()
    
    # Check if user exists
    if not response.data or len(response.data) == 0:
        log_activity('login_failed', metadata={'reason': 'user_not_found', 'email': email})
        return jsonify({'message': 'Invalid email or password'}), 401
        
    user = response.data[0]
    
    # Check if user is active
    if not user.get('is_active'):
        log_activity('login_failed', metadata={'reason': 'user_inactive', 'email': email})
        return jsonify({'message': 'Account is inactive'}), 401
        
    # Check password
    if not user.get('hashed_password') or not bcrypt.checkpw(password.encode('utf-8'), user.get('hashed_password').encode('utf-8')):
        log_activity('login_failed', metadata={'reason': 'invalid_password', 'email': email})
        return jsonify({'message': 'Invalid email or password'}), 401
        
    # Create JWT token
    token = create_access_token(
        user_id=user.get('id'),
        role=user.get('role'),
        campaign_id=user.get('campaign_id')
    )
    
    # Log successful login
    log_activity('login_success', metadata={'email': email})
    
    # Return token and user information
    return jsonify({
        'token': token,
        'user': {
            'id': user.get('id'),
            'email': user.get('email'),
            'full_name': user.get('full_name'),
            'role': user.get('role'),
            'campaign_id': user.get('campaign_id')
        }
    })

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    User registration endpoint (admin only)
    
    Request body:
        {
            "email": "user@example.com",
            "password": "password123",
            "full_name": "John Doe",
            "role": "team_member",
            "pay_rate_per_hour": 18.50,
            "campaign_id": "550e8400-e29b-41d4-a716-446655440001",
            "send_welcome_email": true
        }
        
    Returns:
        Created user information
    """
    data = request.json
    
    # Validate required fields
    required_fields = ['email', 'password', 'full_name', 'role']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'message': f'{field} is required'}), 400
            
    # Validate role
    valid_roles = ['team_member', 'campaign_lead', 'admin']
    if data.get('role') not in valid_roles:
        return jsonify({'message': f'Invalid role. Must be one of: {", ".join(valid_roles)}'}), 400
        
    # Check if campaign_id is provided for non-admin roles
    if data.get('role') != 'admin' and not data.get('campaign_id'):
        return jsonify({'message': 'campaign_id is required for team_member and campaign_lead roles'}), 400
        
    # Get Supabase admin client
    supabase = get_supabase_admin_client()
    
    # Check if email already exists
    response = supabase.table('users').select('id').eq('email', data.get('email')).execute()
    if response.data and len(response.data) > 0:
        return jsonify({'message': 'Email already exists'}), 409
        
    # Hash password
    hashed_password = bcrypt.hashpw(data.get('password').encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Prepare user data
    user_data = {
        'email': data.get('email'),
        'hashed_password': hashed_password,
        'full_name': data.get('full_name'),
        'role': data.get('role'),
        'is_active': True
    }
    
    # Add optional fields if provided
    if data.get('pay_rate_per_hour'):
        user_data['pay_rate_per_hour'] = data.get('pay_rate_per_hour')
        
    if data.get('campaign_id'):
        user_data['campaign_id'] = data.get('campaign_id')
        
    # Insert user
    response = supabase.table('users').insert(user_data).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Failed to create user'}), 500
        
    created_user = response.data[0]
    
    # Send welcome email if requested
    if data.get('send_welcome_email', True):
        send_welcome_email(
            user_email=created_user.get('email'),
            user_name=created_user.get('full_name'),
            temp_password=data.get('password')  # Send the original password
        )
    
    # Log user creation
    log_activity('user_created', 'users', created_user.get('id'))
    
    # Return created user without password
    created_user.pop('hashed_password', None)
    return jsonify(created_user), 201

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """
    User logout endpoint
    
    Returns:
        Success message
    """
    # Log logout activity
    log_activity('logout')
    
    return jsonify({'message': 'Successfully logged out'})

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    """
    Get current user information
    
    Returns:
        Current user information
    """
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Query user by ID
    response = supabase.table('users').select('*').eq('id', g.user_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'User not found'}), 404
        
    user = response.data[0]
    
    # Remove sensitive information
    user.pop('hashed_password', None)
    
    return jsonify(user)

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password_request():
    """
    Request password reset
    
    Request body:
        {
            "email": "user@example.com"
        }
        
    Returns:
        Success message
    """
    data = request.json
    
    if not data or not data.get('email'):
        return jsonify({'message': 'Email is required'}), 400
        
    email = data.get('email')
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Query user by email
    response = supabase.table('users').select('*').eq('email', email).execute()
    
    # Check if user exists
    if not response.data or len(response.data) == 0:
        # For security reasons, always return success even if user doesn't exist
        return jsonify({'message': 'If your email is registered, you will receive a password reset link'}), 200
        
    user = response.data[0]
    
    # Generate a temporary password
    import random
    import string
    temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
    # Hash the temporary password
    hashed_password = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Update user with temporary password
    supabase = get_supabase_admin_client()
    response = supabase.table('users').update({'hashed_password': hashed_password}).eq('id', user.get('id')).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Failed to reset password'}), 500
        
    # Send email with temporary password
    send_welcome_email(
        user_email=user.get('email'),
        user_name=user.get('full_name'),
        temp_password=temp_password
    )
    
    # Log password reset
    log_activity('password_reset_requested', 'users', user.get('id'))
    
    return jsonify({'message': 'If your email is registered, you will receive a password reset link'}), 200

@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password():
    """
    Change user password
    
    Request body:
        {
            "current_password": "current123",
            "new_password": "new123"
        }
        
    Returns:
        Success message
    """
    data = request.json
    
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({'message': 'Current password and new password are required'}), 400
        
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Query user by ID
    response = supabase.table('users').select('*').eq('id', g.user_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'User not found'}), 404
        
    user = response.data[0]
    
    # Check current password
    if not bcrypt.checkpw(current_password.encode('utf-8'), user.get('hashed_password').encode('utf-8')):
        return jsonify({'message': 'Current password is incorrect'}), 401
        
    # Hash new password
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Update user with new password
    supabase = get_supabase_admin_client()
    response = supabase.table('users').update({'hashed_password': hashed_password}).eq('id', g.user_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Failed to change password'}), 500
        
    # Log password change
    log_activity('password_changed', 'users', g.user_id)
    
    return jsonify({'message': 'Password changed successfully'}), 200

