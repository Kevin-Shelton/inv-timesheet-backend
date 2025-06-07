import os
from supabase import create_client, Client

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Create Supabase client
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
else:
    # Fallback for development/testing
    print("Warning: Supabase credentials not found, using mock client")
    supabase = None

def get_supabase_client():
    """Get Supabase client for regular operations"""
    return supabase

def get_supabase_admin_client():
    """Get Supabase client with admin privileges"""
    return supabase

