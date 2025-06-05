import os
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get JWT configuration from environment variables
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))  # Default 1 hour

def create_access_token(user_id, role, campaign_id=None):
    """
    Create a JWT access token for the user
    
    Args:
        user_id (str): User ID
        role (str): User role (team_member, campaign_lead, admin)
        campaign_id (str, optional): Campaign ID for team members and campaign leads
        
    Returns:
        str: JWT access token
    """
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(seconds=JWT_ACCESS_TOKEN_EXPIRES),
        "iat": datetime.utcnow(),
    }
    
    # Add campaign_id to payload if provided
    if campaign_id:
        payload["campaign_id"] = campaign_id
        
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

def decode_token(token):
    """
    Decode and verify a JWT token
    
    Args:
        token (str): JWT token to decode
        
    Returns:
        dict: Decoded token payload
        
    Raises:
        jwt.InvalidTokenError: If token is invalid
        jwt.ExpiredSignatureError: If token has expired
    """
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])

def get_user_id_from_token(token):
    """
    Extract user ID from JWT token
    
    Args:
        token (str): JWT token
        
    Returns:
        str: User ID
        
    Raises:
        jwt.InvalidTokenError: If token is invalid
        jwt.ExpiredSignatureError: If token has expired
    """
    payload = decode_token(token)
    return payload.get("sub")

def get_user_role_from_token(token):
    """
    Extract user role from JWT token
    
    Args:
        token (str): JWT token
        
    Returns:
        str: User role
        
    Raises:
        jwt.InvalidTokenError: If token is invalid
        jwt.ExpiredSignatureError: If token has expired
    """
    payload = decode_token(token)
    return payload.get("role")

def get_campaign_id_from_token(token):
    """
    Extract campaign ID from JWT token
    
    Args:
        token (str): JWT token
        
    Returns:
        str: Campaign ID or None if not present
        
    Raises:
        jwt.InvalidTokenError: If token is invalid
        jwt.ExpiredSignatureError: If token has expired
    """
    payload = decode_token(token)
    return payload.get("campaign_id")

