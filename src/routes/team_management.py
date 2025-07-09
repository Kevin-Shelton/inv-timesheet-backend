from flask import Blueprint, request, jsonify
from utils.supabase import supabase
import uuid
from datetime import datetime

app = Blueprint('team_management', __name__)

@app.route('/team/members', methods=['GET'])
def get_team_members():
    """Get all team members with proper database integration"""
    try:
        # Get all users from the database
        result = supabase.table('users').select('*').execute()
        
        if result.data:
            # Format the data for frontend
            members = []
            for user in result.data:
                member = {
                    'id': user['id'],
                    'full_name': user['full_name'],
                    'email': user['email'],
                    'role': user['role'],
                    'department': user.get('department', ''),
                    'pay_rate_per_hour': float(user.get('pay_rate_per_hour', 0)),
                    'hire_date': user.get('hire_date', ''),
                    'phone': user.get('phone', ''),
                    'is_active': user.get('is_active', True),
                    'created_at': user.get('created_at', ''),
                    'updated_at': user.get('updated_at', '')
                }
                members.append(member)
            
            return jsonify(members), 200
        else:
            return jsonify([]), 200
            
    except Exception as e:
        print(f"Error fetching team members: {str(e)}")
        return jsonify({'error': 'Failed to fetch team members'}), 500

@app.route('/team/members', methods=['POST'])
def create_team_member():
    """Create a new team member"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['full_name', 'email', 'role']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if email already exists
        existing_user = supabase.table('users').select('id').eq('email', data['email']).execute()
        if existing_user.data:
            return jsonify({'error': 'Email already exists'}), 400
        
        # Prepare user data
        user_data = {
            'id': str(uuid.uuid4()),
            'full_name': data['full_name'],
            'email': data['email'],
            'role': data['role'],
            'department': data.get('department', ''),
            'pay_rate_per_hour': float(data.get('pay_rate_per_hour', 0)),
            'hire_date': data.get('hire_date', ''),
            'phone': data.get('phone', ''),
            'is_active': True,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Insert into database
        result = supabase.table('users').insert(user_data).execute()
        
        if result.data:
            return jsonify(result.data[0]), 201
        else:
            return jsonify({'error': 'Failed to create team member'}), 500
            
    except Exception as e:
        print(f"Error creating team member: {str(e)}")
        return jsonify({'error': 'Failed to create team member'}), 500

@app.route('/team/members/<member_id>', methods=['PUT'])
def update_team_member(member_id):
    """Update a team member"""
    try:
        data = request.get_json()
        
        # Prepare update data
        update_data = {
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Add fields that can be updated
        updatable_fields = ['full_name', 'email', 'role', 'department', 'pay_rate_per_hour', 'hire_date', 'phone', 'is_active']
        for field in updatable_fields:
            if field in data:
                if field == 'pay_rate_per_hour':
                    update_data[field] = float(data[field])
                else:
                    update_data[field] = data[field]
        
        # Update in database
        result = supabase.table('users').update(update_data).eq('id', member_id).execute()
        
        if result.data:
            return jsonify(result.data[0]), 200
        else:
            return jsonify({'error': 'Team member not found'}), 404
            
    except Exception as e:
        print(f"Error updating team member: {str(e)}")
        return jsonify({'error': 'Failed to update team member'}), 500

@app.route('/team/members/<member_id>/deactivate', methods=['PUT'])
def deactivate_team_member(member_id):
    """Mark a team member as inactive instead of deleting"""
    try:
        # Update is_active to False
        update_data = {
            'is_active': False,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = supabase.table('users').update(update_data).eq('id', member_id).execute()
        
        if result.data:
            return jsonify({'message': 'Team member deactivated successfully'}), 200
        else:
            return jsonify({'error': 'Team member not found'}), 404
            
    except Exception as e:
        print(f"Error deactivating team member: {str(e)}")
        return jsonify({'error': 'Failed to deactivate team member'}), 500

@app.route('/team/members/<member_id>/activate', methods=['PUT'])
def activate_team_member(member_id):
    """Reactivate a team member"""
    try:
        # Update is_active to True
        update_data = {
            'is_active': True,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = supabase.table('users').update(update_data).eq('id', member_id).execute()
        
        if result.data:
            return jsonify({'message': 'Team member activated successfully'}), 200
        else:
            return jsonify({'error': 'Team member not found'}), 404
            
    except Exception as e:
        print(f"Error activating team member: {str(e)}")
        return jsonify({'error': 'Failed to activate team member'}), 500

# Campaign Management Routes
@app.route('/campaigns', methods=['GET'])
def get_campaigns():
    """Get all campaigns"""
    try:
        result = supabase.table('campaigns').select('*').execute()
        
        if result.data:
            return jsonify(result.data), 200
        else:
            return jsonify([]), 200
            
    except Exception as e:
        print(f"Error fetching campaigns: {str(e)}")
        return jsonify({'error': 'Failed to fetch campaigns'}), 500

@app.route('/campaigns', methods=['POST'])
def create_campaign():
    """Create a new campaign"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'client_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Prepare campaign data
        campaign_data = {
            'id': str(uuid.uuid4()),
            'name': data['name'],
            'client_name': data['client_name'],
            'description': data.get('description', ''),
            'billing_rate': float(data.get('billing_rate', 0)),
            'start_date': data.get('start_date', ''),
            'end_date': data.get('end_date', ''),
            'is_active': True,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Insert into database
        result = supabase.table('campaigns').insert(campaign_data).execute()
        
        if result.data:
            return jsonify(result.data[0]), 201
        else:
            return jsonify({'error': 'Failed to create campaign'}), 500
            
    except Exception as e:
        print(f"Error creating campaign: {str(e)}")
        return jsonify({'error': 'Failed to create campaign'}), 500

@app.route('/campaigns/<campaign_id>/task-templates', methods=['GET'])
def get_campaign_task_templates(campaign_id):
    """Get task templates for a campaign"""
    try:
        result = supabase.table('task_templates').select('*').eq('campaign_id', campaign_id).execute()
        
        if result.data:
            return jsonify(result.data), 200
        else:
            return jsonify([]), 200
            
    except Exception as e:
        print(f"Error fetching task templates: {str(e)}")
        return jsonify({'error': 'Failed to fetch task templates'}), 500

@app.route('/campaigns/<campaign_id>/task-templates', methods=['POST'])
def create_task_template(campaign_id):
    """Create a task template for a campaign"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Prepare task template data
        template_data = {
            'id': str(uuid.uuid4()),
            'campaign_id': campaign_id,
            'name': data['name'],
            'description': data['description'],
            'estimated_hours': float(data.get('estimated_hours', 0)),
            'is_billable': data.get('is_billable', True),
            'is_active': True,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Insert into database
        result = supabase.table('task_templates').insert(template_data).execute()
        
        if result.data:
            return jsonify(result.data[0]), 201
        else:
            return jsonify({'error': 'Failed to create task template'}), 500
            
    except Exception as e:
        print(f"Error creating task template: {str(e)}")
        return jsonify({'error': 'Failed to create task template'}), 500

@app.route('/campaigns/<campaign_id>/members', methods=['GET'])
def get_campaign_members(campaign_id):
    """Get team members assigned to a campaign"""
    try:
        # Get campaign assignments with user details
        result = supabase.table('campaign_assignments').select('''
            *,
            users (
                id,
                full_name,
                email,
                role,
                is_active
            )
        ''').eq('campaign_id', campaign_id).execute()
        
        if result.data:
            return jsonify(result.data), 200
        else:
            return jsonify([]), 200
            
    except Exception as e:
        print(f"Error fetching campaign members: {str(e)}")
        return jsonify({'error': 'Failed to fetch campaign members'}), 500

@app.route('/campaigns/<campaign_id>/members', methods=['POST'])
def assign_member_to_campaign(campaign_id):
    """Assign a team member to a campaign"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('user_id'):
            return jsonify({'error': 'user_id is required'}), 400
        
        # Check if assignment already exists
        existing = supabase.table('campaign_assignments').select('id').eq('campaign_id', campaign_id).eq('user_id', data['user_id']).execute()
        if existing.data:
            return jsonify({'error': 'User already assigned to this campaign'}), 400
        
        # Prepare assignment data
        assignment_data = {
            'id': str(uuid.uuid4()),
            'campaign_id': campaign_id,
            'user_id': data['user_id'],
            'role': data.get('role', 'team_member'),
            'start_date': data.get('start_date', datetime.utcnow().isoformat()),
            'end_date': data.get('end_date', ''),
            'is_active': True,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Insert into database
        result = supabase.table('campaign_assignments').insert(assignment_data).execute()
        
        if result.data:
            return jsonify(result.data[0]), 201
        else:
            return jsonify({'error': 'Failed to assign member to campaign'}), 500
            
    except Exception as e:
        print(f"Error assigning member to campaign: {str(e)}")
        return jsonify({'error': 'Failed to assign member to campaign'}), 500

