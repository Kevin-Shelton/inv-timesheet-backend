from flask import Blueprint, request, jsonify, g
from src.utils.supabase import get_supabase_client
from src.middleware.auth import token_required, admin_required, campaign_lead_required, log_activity

schedules_bp = Blueprint('schedules', __name__)

@schedules_bp.route('', methods=['GET'])
@token_required
def get_schedules():
    """
    Get schedules based on role:
    - Admin: All schedules or filtered by campaign_id
    - Campaign Lead: Only schedules for their campaign
    - Team Member: Only schedules for their campaign
    
    Query parameters:
        campaign_id (optional): Filter schedules by campaign ID
        
    Returns:
        List of schedules
    """
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Start building query
    query = supabase.table('schedules').select('*')
    
    # Apply role-based filtering
    if g.user_role == 'admin':
        # Admin can see all schedules or filter by campaign_id
        if request.args.get('campaign_id'):
            query = query.eq('campaign_id', request.args.get('campaign_id'))
    else:
        # Non-admin users can only see schedules for their campaign
        query = query.eq('campaign_id', g.campaign_id)
        
    # Execute query
    response = query.execute()
    
    return jsonify(response.data)

@schedules_bp.route('/<schedule_id>', methods=['GET'])
@token_required
def get_schedule(schedule_id):
    """
    Get a specific schedule
    
    Path parameters:
        schedule_id: ID of the schedule to retrieve
        
    Returns:
        Schedule information
    """
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Query schedule
    response = supabase.table('schedules').select('*').eq('id', schedule_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Schedule not found'}), 404
        
    schedule = response.data[0]
    
    # Check permissions for non-admin users
    if g.user_role != 'admin' and schedule.get('campaign_id') != g.campaign_id:
        return jsonify({'message': 'Access denied'}), 403
        
    return jsonify(schedule)

@schedules_bp.route('', methods=['POST'])
@token_required
@admin_required
def create_schedule():
    """
    Create a new schedule (admin only)
    
    Request body:
        {
            "campaign_id": "550e8400-e29b-41d4-a716-446655440001",
            "name": "Standard 9-6 Shift",
            "work_start_time": "09:00:00",
            "work_end_time": "18:00:00",
            "lunch_duration_minutes": 60,
            "short_break_duration_minutes": 15
        }
        
    Returns:
        Created schedule information
    """
    data = request.json
    
    # Validate required fields
    required_fields = ['campaign_id', 'name', 'work_start_time', 'work_end_time']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'message': f'{field} is required'}), 400
            
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check if campaign exists
    response = supabase.table('campaigns').select('id').eq('id', data.get('campaign_id')).execute()
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Campaign not found'}), 404
        
    # Check if schedule name already exists for this campaign
    response = supabase.table('schedules').select('id').eq('campaign_id', data.get('campaign_id')).eq('name', data.get('name')).execute()
    if response.data and len(response.data) > 0:
        return jsonify({'message': 'Schedule name already exists for this campaign'}), 409
        
    # Prepare schedule data
    schedule_data = {
        'campaign_id': data.get('campaign_id'),
        'name': data.get('name'),
        'work_start_time': data.get('work_start_time'),
        'work_end_time': data.get('work_end_time'),
        'lunch_duration_minutes': data.get('lunch_duration_minutes', 60),
        'short_break_duration_minutes': data.get('short_break_duration_minutes', 15)
    }
        
    # Insert schedule
    response = supabase.table('schedules').insert(schedule_data).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Failed to create schedule'}), 500
        
    created_schedule = response.data[0]
    
    # Log schedule creation
    log_activity('schedule_created', 'schedules', created_schedule.get('id'))
    
    return jsonify(created_schedule), 201

@schedules_bp.route('/<schedule_id>', methods=['PUT'])
@token_required
@admin_required
def update_schedule(schedule_id):
    """
    Update a schedule (admin only)
    
    Path parameters:
        schedule_id: ID of the schedule to update
        
    Request body:
        {
            "name": "Updated Schedule Name",
            "work_start_time": "08:00:00",
            "work_end_time": "17:00:00",
            "lunch_duration_minutes": 45,
            "short_break_duration_minutes": 10
        }
        
    Returns:
        Updated schedule information
    """
    data = request.json
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check if schedule exists
    response = supabase.table('schedules').select('*').eq('id', schedule_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Schedule not found'}), 404
        
    existing_schedule = response.data[0]
    
    # Prepare update data
    update_data = {}
    
    allowed_fields = ['name', 'work_start_time', 'work_end_time', 'lunch_duration_minutes', 'short_break_duration_minutes']
    for field in allowed_fields:
        if field in data:
            update_data[field] = data.get(field)
    
    # If no fields to update
    if not update_data:
        return jsonify({'message': 'No fields to update'}), 400
        
    # If updating name, check if new name already exists for this campaign
    if 'name' in update_data:
        response = supabase.table('schedules').select('id').eq('campaign_id', existing_schedule.get('campaign_id')).eq('name', update_data['name']).neq('id', schedule_id).execute()
        if response.data and len(response.data) > 0:
            return jsonify({'message': 'Schedule name already exists for this campaign'}), 409
        
    # Update schedule
    response = supabase.table('schedules').update(update_data).eq('id', schedule_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Failed to update schedule'}), 500
        
    updated_schedule = response.data[0]
    
    # Log schedule update
    log_activity('schedule_updated', 'schedules', schedule_id)
    
    return jsonify(updated_schedule)

@schedules_bp.route('/<schedule_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_schedule(schedule_id):
    """
    Delete a schedule (admin only)
    
    Path parameters:
        schedule_id: ID of the schedule to delete
        
    Returns:
        Success message
    """
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check if schedule exists
    response = supabase.table('schedules').select('id').eq('id', schedule_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Schedule not found'}), 404
        
    # Delete schedule
    response = supabase.table('schedules').delete().eq('id', schedule_id).execute()
    
    # Log schedule deletion
    log_activity('schedule_deleted', 'schedules', schedule_id)
    
    return jsonify({'message': 'Schedule deleted successfully'}), 200

