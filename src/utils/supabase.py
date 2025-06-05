import os
from datetime import datetime, timedelta
import jwt
import bcrypt

# Mock Supabase client for development
class MockSupabaseClient:
    def __init__(self):
        # Mock users data
        self.users = [
            {
                'id': '1',
                'email': 'admin@example.com',
                'password_hash': bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                'full_name': 'Admin User',
                'role': 'admin',
                'pay_rate_per_hour': 25.00,
                'campaign_id': None,
                'is_active': True,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': '2',
                'email': 'john.doe@example.com',
                'password_hash': bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                'full_name': 'John Doe',
                'role': 'team_member',
                'pay_rate_per_hour': 18.50,
                'campaign_id': '1',
                'is_active': True,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': '3',
                'email': 'jane.smith@example.com',
                'password_hash': bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                'full_name': 'Jane Smith',
                'role': 'campaign_lead',
                'pay_rate_per_hour': 22.00,
                'campaign_id': '1',
                'is_active': True,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        ]
        
        # Mock campaigns data
        self.campaigns = [
            {
                'id': '1',
                'name': 'Customer Support Campaign',
                'billing_rate_per_hour': 30.00,
                'is_active': True,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        ]
        
        # Mock audit logs data
        self.audit_logs = []

    def table(self, table_name):
        return MockTable(self, table_name)

class MockTable:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.query_filters = []
        self.query_select = '*'
        self.query_limit = None

    def select(self, columns='*'):
        self.query_select = columns
        return self

    def eq(self, column, value):
        self.query_filters.append(('eq', column, value))
        return self

    def limit(self, count):
        self.query_limit = count
        return self

    def execute(self):
        data = getattr(self.client, self.table_name, [])
        
        # Apply filters
        for filter_type, column, value in self.query_filters:
            if filter_type == 'eq':
                data = [item for item in data if item.get(column) == value]
        
        # Apply limit
        if self.query_limit:
            data = data[:self.query_limit]
        
        return MockResponse(data)

    def insert(self, data):
        table_data = getattr(self.client, self.table_name, [])
        
        # Generate ID if not provided
        if 'id' not in data:
            data['id'] = str(len(table_data) + 1)
        
        # Add timestamps
        data['created_at'] = datetime.now().isoformat()
        data['updated_at'] = datetime.now().isoformat()
        
        table_data.append(data)
        return MockResponse([data])

    def update(self, data):
        table_data = getattr(self.client, self.table_name, [])
        
        # Apply filters to find items to update
        for i, item in enumerate(table_data):
            match = True
            for filter_type, column, value in self.query_filters:
                if filter_type == 'eq' and item.get(column) != value:
                    match = False
                    break
            
            if match:
                item.update(data)
                item['updated_at'] = datetime.now().isoformat()
        
        return MockResponse([])

    def delete(self):
        table_data = getattr(self.client, self.table_name, [])
        
        # Apply filters to find items to delete
        items_to_remove = []
        for item in table_data:
            match = True
            for filter_type, column, value in self.query_filters:
                if filter_type == 'eq' and item.get(column) != value:
                    match = False
                    break
            
            if match:
                items_to_remove.append(item)
        
        for item in items_to_remove:
            table_data.remove(item)
        
        return MockResponse([])

class MockResponse:
    def __init__(self, data):
        self.data = data
    
    def execute(self):
        """Execute method to match Supabase client interface"""
        return self

# Create mock client instance
mock_supabase = MockSupabaseClient()

def get_supabase_client():
    """Get Supabase client for regular operations"""
    return mock_supabase

def get_supabase_admin_client():
    """Get Supabase client with admin privileges"""
    return mock_supabase

def create_audit_log(user_id, action, resource_type, resource_id=None, details=None):
    """Create an audit log entry"""
    audit_data = {
        'user_id': user_id,
        'action': action,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'details': details,
        'ip_address': '127.0.0.1',  # Mock IP
        'user_agent': 'Mock User Agent',
        'timestamp': datetime.now().isoformat()
    }
    
    # In a real implementation, this would save to the audit_logs table
    print(f"Audit Log: {audit_data}")
    return audit_data

