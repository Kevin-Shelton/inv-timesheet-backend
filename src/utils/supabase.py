import os

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Initialize Supabase client with error handling
supabase = None

try:
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        print("✅ Supabase client initialized successfully")
    else:
        print("❌ Missing Supabase credentials:")
        print(f"SUPABASE_URL: {'✅' if SUPABASE_URL else '❌'}")
        print(f"SUPABASE_SERVICE_ROLE_KEY: {'✅' if SUPABASE_SERVICE_ROLE_KEY else '❌'}")
except Exception as e:
    print(f"❌ Failed to initialize Supabase client: {str(e)}")
    supabase = None

def get_supabase_client():
    """Get Supabase client for regular operations"""
    if supabase is None:
        raise Exception("Supabase client not initialized. Check your environment variables.")
    return supabase

def get_supabase_admin_client():
    """Get Supabase client with admin privileges"""
    if supabase is None:
        raise Exception("Supabase client not initialized. Check your environment variables.")
    return supabase
