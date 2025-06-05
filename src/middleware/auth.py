from functools import wraps
from flask import request, jsonify, g
import jwt
from src.utils.jwt_utils import decode_token

def token_required(f):
    """
    Decorator to protect routes that require authentication
    
    Usage:
        @app.route('/protected')
        @token_required
        def protected():
            return jsonify({"message": "This is a protected route"})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check if token is in the Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
        if not token:
            return jsonify({'message': 'Authentication token is missing'}), 401
            
        try:
            # Decode the token
            payload = decode_token(token)
            
            # Store user info in Flask's g object for use in the route
            g.user_id = payload['sub']
            g.user_role = payload['role']
            g.campaign_id = payload.get('campaign_id')
            
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Authentication token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid authentication token'}), 401
            
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    """
    Decorator to protect routes that require admin role
    
    Usage:
        @app.route('/admin-only')
        @token_required
        @admin_required
        def admin_only():
            return jsonify({"message": "This is an admin-only route"})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.user_role or g.user_role != 'admin':
            return jsonify({'message': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    
    return decorated

def campaign_lead_required(f):
    """
    Decorator to protect routes that require campaign lead role
    
    Usage:
        @app.route('/campaign-lead-only')
        @token_required
        @campaign_lead_required
        def campaign_lead_only():
            return jsonify({"message": "This is a campaign lead-only route"})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.user_role or g.user_role not in ['admin', 'campaign_lead']:
            return jsonify({'message': 'Campaign lead privileges required'}), 403
        return f(*args, **kwargs)
    
    return decorated

def log_activity(action, object_type=None, object_id=None, metadata=None):
    """
    Log user activity to audit_logs table
    
    Args:
        action (str): Action performed (e.g., 'login_success', 'timesheet_submitted')
        object_type (str, optional): Type of object affected (e.g., 'timesheet_entries')
        object_id (str, optional): ID of the object affected
        metadata (dict, optional): Additional context information
    """
    from src.utils.supabase import get_supabase_client
    
    supabase = get_supabase_client()
    
    # Get user ID from Flask's g object if available
    user_id = getattr(g, 'user_id', None)
    
    # Get IP address and user agent from request
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent')
    
    # Create audit log entry
    supabase.table('audit_logs').insert({
        'user_id': user_id,
        'action': action,
        'object_type': object_type,
        'object_id': object_id,
        'ip_address': ip_address,
        'user_agent': user_agent,
        'metadata': metadata
    }).execute()

