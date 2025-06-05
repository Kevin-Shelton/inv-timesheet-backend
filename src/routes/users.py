from flask import Blueprint, request, jsonify, g
import bcrypt
from src.utils.supabase import get_supabase_client, get_supabase_admin_client
from src.middleware.auth import token_required, admin_required, campaign_lead_required, log_activity

users_bp = Blueprint('users', __name__)

@users_bp.route('', methods=['GET'])
@token_required
def get_users():
    """
    Get users based on role:
    - Admin: All users
    - Campaign Lead: Users in their campaign
    - Team Member: Only themselves
    
    Query parameters:
        campaign_id (optional): Filter users by campaign ID
        role (optional): Filter users by role
        
    Returns:
        List of users
    """
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Start building query
    query = supabase.table('users').select('*')
    
    # Apply role-based filtering
    if g.user_role == 'admin':
        # Admin can see all users
        pass
    elif g.user_role == 'campaign_lead':
        # Campaign lead can only see users in their campaign
        query = query.eq('campaign_id', g.campaign_id)
    else:
        # Team member can only see themselves
        query = query.eq('id', g.user_id)
        
    # Apply additional filters if provided
    if request.args.get('campaign_id') and g.user_role == 'admin':
        query = query.eq('campaign_id', request.args.get('campaign_id'))
        
    if request.args.get('role'):
        query = query.eq('role', request.args.get('role'))
        
    # Execute query
    response = query.execute()
    
    # Remove sensitive information
    users = response.data
    for user in users:
        user.pop('hashed_password', None)
        
    return jsonify(users)

@users_bp.route('/<user_id>', methods=['GET'])
@token_required
def get_user(user_id):
    """
    Get a specific user
    
    Path parameters:
        user_id: ID of the user to retrieve
        
    Returns:
        User information
    """
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check permissions
    if g.user_role == 'team_member' and g.user_id != user_id:
        return jsonify({'message': 'Access denied'}), 403
        
    if g.user_role == 'campaign_lead':
        # Check if user is in the campaign lead's campaign
        response = supabase.table('users').select('campaign_id').eq('id', user_id).execute()
        
        if not response.data or len(response.data) == 0:
            return jsonify({'message': 'User not found'}), 404
            
        if response.data[0].get('campaign_id') != g.campaign_id:
            return jsonify({'message': 'Access denied'}), 403
    
    # Query user
    response = supabase.table('users').select('*').eq('id', user_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'User not found'}), 404
        
    user = response.data[0]
    
    # Remove sensitive information
    user.pop('hashed_password', None)
    
    return jsonify(user)

@users_bp.route('', methods=['POST'])
@token_required
@admin_required
def create_user():
    """
    Create a new user (admin only)
    
    Request body:
        {
            "email": "user@example.com",
            "password": "password123",
            "full_name": "John Doe",
            "role": "team_member",
            "pay_rate_per_hour": 18.50,
            "campaign_id": "550e8400-e29b-41d4-a716-446655440001"
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
    
    # Log user creation
    log_activity('user_created', 'users', created_user.get('id'))
    
    # Remove sensitive information
    created_user.pop('hashed_password', None)
    
    return jsonify(created_user), 201

@users_bp.route('/<user_id>', methods=['PUT'])
@token_required
def update_user(user_id):
    """
    Update a user
    
    Path parameters:
        user_id: ID of the user to update
        
    Request body:
        {
            "full_name": "John Doe Updated",
            "role": "campaign_lead",
            "pay_rate_per_hour": 20.00,
            "campaign_id": "550e8400-e29b-41d4-a716-446655440002",
            "is_active": true,
            "password": "new_password" (optional)
        }
        
    Returns:
        Updated user information
    """
    data = request.json
    
    # Check permissions
    if g.user_role == 'team_member' and g.user_id != user_id:
        return jsonify({'message': 'Access denied'}), 403
        
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check if user exists
    response = supabase.table('users').select('*').eq('id', user_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'User not found'}), 404
        
    existing_user = response.data[0]
    
    # Campaign lead can only update users in their campaign
    if g.user_role == 'campaign_lead' and existing_user.get('campaign_id') != g.campaign_id:
        return jsonify({'message': 'Access denied'}), 403
        
    # Prepare update data
    update_data = {}
    
    # Team members can only update their own full_name
    if g.user_role == 'team_member':
        if data.get('full_name'):
            update_data['full_name'] = data.get('full_name')
            
        # Team members can update their own password
        if data.get('password'):
            update_data['hashed_password'] = bcrypt.hashpw(data.get('password').encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    else:
        # Campaign leads and admins can update more fields
        allowed_fields = ['full_name', 'is_active', 'pay_rate_per_hour']
        
        # Only admins can update role and campaign_id
        if g.user_role == 'admin':
            allowed_fields.extend(['role', 'campaign_id'])
            
        for field in allowed_fields:
            if field in data:
                update_data[field] = data.get(field)
                
        # Update password if provided
        if data.get('password'):
            update_data['hashed_password'] = bcrypt.hashpw(data.get('password').encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # If no fields to update
    if not update_data:
        return jsonify({'message': 'No fields to update'}), 400
        
    # Update user
    response = supabase.table('users').update(update_data).eq('id', user_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Failed to update user'}), 500
        
    updated_user = response.data[0]
    
    # Log user update
    log_activity('user_updated', 'users', user_id)
    
    # Remove sensitive information
    updated_user.pop('hashed_password', None)
    
    return jsonify(updated_user)

@users_bp.route('/<user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(user_id):
    """
    Delete a user (admin only)
    
    Path parameters:
        user_id: ID of the user to delete
        
    Returns:
        Success message
    """
    # Get Supabase admin client
    supabase = get_supabase_admin_client()
    
    # Check if user exists
    response = supabase.table('users').select('id').eq('id', user_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'User not found'}), 404
        
    # Delete user
    response = supabase.table('users').delete().eq('id', user_id).execute()
    
    # Log user deletion
    log_activity('user_deleted', 'users', user_id)
    
    return jsonify({'message': 'User deleted successfully'}), 200

