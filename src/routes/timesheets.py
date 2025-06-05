from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from src.utils.supabase import get_supabase_client
from src.middleware.auth import token_required, admin_required, campaign_lead_required, log_activity
from src.utils.email_utils import (
    send_timesheet_submitted_notification,
    send_timesheet_approved_notification,
    send_timesheet_rejected_notification
)

timesheets_bp = Blueprint('timesheets', __name__)

def calculate_hours(timesheet):
    """
    Calculate total paid hours and unpaid breaks for a timesheet entry
    
    Args:
        timesheet (dict): Timesheet entry with time_in, time_out, lunch_start, lunch_end, etc.
        
    Returns:
        tuple: (total_paid_hours, total_unpaid_breaks)
    """
    # If vacation day, return 8 hours
    if timesheet.get('vacation_type') != 'none':
        return 8.0, 0.0
        
    # If missing required fields, return 0
    if not timesheet.get('time_in') or not timesheet.get('time_out'):
        return 0.0, 0.0
        
    # Parse timestamps
    time_in = datetime.fromisoformat(timesheet.get('time_in').replace('Z', '+00:00'))
    time_out = datetime.fromisoformat(timesheet.get('time_out').replace('Z', '+00:00'))
    
    # Calculate total work duration in hours
    total_duration = (time_out - time_in).total_seconds() / 3600
    
    # Calculate lunch break duration
    lunch_duration = 0.0
    if timesheet.get('lunch_start') and timesheet.get('lunch_end'):
        lunch_start = datetime.fromisoformat(timesheet.get('lunch_start').replace('Z', '+00:00'))
        lunch_end = datetime.fromisoformat(timesheet.get('lunch_end').replace('Z', '+00:00'))
        lunch_duration = (lunch_end - lunch_start).total_seconds() / 3600
        
    # Calculate break1 duration
    break1_duration = 0.0
    if timesheet.get('break1_start') and timesheet.get('break1_end'):
        break1_start = datetime.fromisoformat(timesheet.get('break1_start').replace('Z', '+00:00'))
        break1_end = datetime.fromisoformat(timesheet.get('break1_end').replace('Z', '+00:00'))
        break1_duration = (break1_end - break1_start).total_seconds() / 3600
        
    # Calculate break2 duration
    break2_duration = 0.0
    if timesheet.get('break2_start') and timesheet.get('break2_end'):
        break2_start = datetime.fromisoformat(timesheet.get('break2_start').replace('Z', '+00:00'))
        break2_end = datetime.fromisoformat(timesheet.get('break2_end').replace('Z', '+00:00'))
        break2_duration = (break2_end - break2_start).total_seconds() / 3600
        
    # Calculate total unpaid breaks
    total_unpaid_breaks = lunch_duration + break1_duration + break2_duration
    
    # Calculate total paid hours
    total_paid_hours = total_duration - total_unpaid_breaks
    
    # Round to 2 decimal places
    total_paid_hours = round(total_paid_hours, 2)
    total_unpaid_breaks = round(total_unpaid_breaks, 2)
    
    return total_paid_hours, total_unpaid_breaks

@timesheets_bp.route('', methods=['GET'])
@token_required
def get_timesheets():
    """
    Get timesheet entries based on role:
    - Admin: All timesheets or filtered by user_id, campaign_id, date range
    - Campaign Lead: Only timesheets for their campaign
    - Team Member: Only their own timesheets
    
    Query parameters:
        user_id (optional): Filter timesheets by user ID
        campaign_id (optional): Filter timesheets by campaign ID
        start_date (optional): Filter timesheets by start date (YYYY-MM-DD)
        end_date (optional): Filter timesheets by end date (YYYY-MM-DD)
        status (optional): Filter timesheets by status
        
    Returns:
        List of timesheet entries
    """
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Start building query
    query = supabase.table('timesheet_entries').select('*')
    
    # Apply role-based filtering
    if g.user_role == 'admin':
        # Admin can see all timesheets or filter by user_id, campaign_id
        if request.args.get('user_id'):
            query = query.eq('user_id', request.args.get('user_id'))
            
        if request.args.get('campaign_id'):
            query = query.eq('campaign_id', request.args.get('campaign_id'))
    elif g.user_role == 'campaign_lead':
        # Campaign lead can only see timesheets for their campaign
        query = query.eq('campaign_id', g.campaign_id)
        
        # Campaign lead can filter by user_id within their campaign
        if request.args.get('user_id'):
            query = query.eq('user_id', request.args.get('user_id'))
    else:
        # Team member can only see their own timesheets
        query = query.eq('user_id', g.user_id)
        
    # Apply date range filtering
    if request.args.get('start_date'):
        query = query.gte('date', request.args.get('start_date'))
        
    if request.args.get('end_date'):
        query = query.lte('date', request.args.get('end_date'))
        
    # Apply status filtering
    if request.args.get('status'):
        query = query.eq('status', request.args.get('status'))
        
    # Execute query
    response = query.execute()
    
    return jsonify(response.data)

@timesheets_bp.route('/<timesheet_id>', methods=['GET'])
@token_required
def get_timesheet(timesheet_id):
    """
    Get a specific timesheet entry
    
    Path parameters:
        timesheet_id: ID of the timesheet entry to retrieve
        
    Returns:
        Timesheet entry information
    """
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Query timesheet
    response = supabase.table('timesheet_entries').select('*').eq('id', timesheet_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Timesheet entry not found'}), 404
        
    timesheet = response.data[0]
    
    # Check permissions
    if g.user_role == 'team_member' and timesheet.get('user_id') != g.user_id:
        return jsonify({'message': 'Access denied'}), 403
        
    if g.user_role == 'campaign_lead' and timesheet.get('campaign_id') != g.campaign_id:
        return jsonify({'message': 'Access denied'}), 403
        
    return jsonify(timesheet)

@timesheets_bp.route('', methods=['POST'])
@token_required
def create_timesheet():
    """
    Create a new timesheet entry
    
    Request body:
        {
            "user_id": "770e8400-e29b-41d4-a716-446655440004", (optional for team members, required for admins/leads)
            "campaign_id": "550e8400-e29b-41d4-a716-446655440001", (optional for team members, required for admins/leads)
            "date": "2025-06-05",
            "time_in": "2025-06-05T09:00:00Z", (optional if vacation day)
            "time_out": "2025-06-05T18:00:00Z", (optional if vacation day)
            "lunch_start": "2025-06-05T12:00:00Z", (optional)
            "lunch_end": "2025-06-05T13:00:00Z", (optional)
            "break1_start": "2025-06-05T10:30:00Z", (optional)
            "break1_end": "2025-06-05T10:45:00Z", (optional)
            "break2_start": "2025-06-05T15:00:00Z", (optional)
            "break2_end": "2025-06-05T15:15:00Z", (optional)
            "vacation_type": "none" (optional, default "none")
        }
        
    Returns:
        Created timesheet entry information
    """
    data = request.json
    
    # Validate required fields
    if not data.get('date'):
        return jsonify({'message': 'date is required'}), 400
        
    # Determine user_id and campaign_id based on role
    user_id = data.get('user_id')
    campaign_id = data.get('campaign_id')
    
    if g.user_role == 'team_member':
        # Team members can only create their own timesheets
        user_id = g.user_id
        campaign_id = g.campaign_id
    elif g.user_role == 'campaign_lead':
        # Campaign leads can create timesheets for users in their campaign
        campaign_id = g.campaign_id
        
        # Validate user_id is provided
        if not user_id:
            return jsonify({'message': 'user_id is required'}), 400
            
        # Check if user belongs to the campaign lead's campaign
        supabase = get_supabase_client()
        response = supabase.table('users').select('campaign_id').eq('id', user_id).execute()
        
        if not response.data or len(response.data) == 0:
            return jsonify({'message': 'User not found'}), 404
            
        if response.data[0].get('campaign_id') != g.campaign_id:
            return jsonify({'message': 'User does not belong to your campaign'}), 403
    else:  # Admin
        # Validate user_id and campaign_id are provided
        if not user_id:
            return jsonify({'message': 'user_id is required'}), 400
            
        if not campaign_id:
            return jsonify({'message': 'campaign_id is required'}), 400
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check if timesheet entry already exists for this user and date
    response = supabase.table('timesheet_entries').select('id').eq('user_id', user_id).eq('date', data.get('date')).execute()
    if response.data and len(response.data) > 0:
        return jsonify({'message': 'Timesheet entry already exists for this date'}), 409
        
    # Prepare timesheet data
    timesheet_data = {
        'user_id': user_id,
        'campaign_id': campaign_id,
        'date': data.get('date'),
        'status': 'draft',
        'vacation_type': data.get('vacation_type', 'none')
    }
    
    # Add optional fields if provided
    optional_fields = [
        'time_in', 'time_out', 
        'lunch_start', 'lunch_end', 
        'break1_start', 'break1_end', 
        'break2_start', 'break2_end'
    ]
    
    for field in optional_fields:
        if field in data:
            timesheet_data[field] = data.get(field)
    
    # Calculate total paid hours and unpaid breaks
    total_paid_hours, total_unpaid_breaks = calculate_hours(timesheet_data)
    timesheet_data['total_paid_hours'] = total_paid_hours
    timesheet_data['total_unpaid_breaks'] = total_unpaid_breaks
        
    # Insert timesheet entry
    response = supabase.table('timesheet_entries').insert(timesheet_data).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Failed to create timesheet entry'}), 500
        
    created_timesheet = response.data[0]
    
    # Log timesheet creation
    log_activity('timesheet_created', 'timesheet_entries', created_timesheet.get('id'))
    
    return jsonify(created_timesheet), 201

@timesheets_bp.route('/<timesheet_id>', methods=['PUT'])
@token_required
def update_timesheet(timesheet_id):
    """
    Update a timesheet entry
    
    Path parameters:
        timesheet_id: ID of the timesheet entry to update
        
    Request body:
        {
            "time_in": "2025-06-05T09:15:00Z",
            "time_out": "2025-06-05T18:15:00Z",
            "lunch_start": "2025-06-05T12:30:00Z",
            "lunch_end": "2025-06-05T13:30:00Z",
            "break1_start": "2025-06-05T10:30:00Z",
            "break1_end": "2025-06-05T10:45:00Z",
            "break2_start": "2025-06-05T15:00:00Z",
            "break2_end": "2025-06-05T15:15:00Z",
            "vacation_type": "vacation"
        }
        
    Returns:
        Updated timesheet entry information
    """
    data = request.json
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check if timesheet exists
    response = supabase.table('timesheet_entries').select('*').eq('id', timesheet_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Timesheet entry not found'}), 404
        
    existing_timesheet = response.data[0]
    
    # Check permissions
    if g.user_role == 'team_member':
        # Team members can only update their own timesheets
        if existing_timesheet.get('user_id') != g.user_id:
            return jsonify({'message': 'Access denied'}), 403
            
        # Team members can only update draft or rejected timesheets
        if existing_timesheet.get('status') not in ['draft', 'rejected']:
            return jsonify({'message': 'Cannot update timesheet in current status'}), 400
    elif g.user_role == 'campaign_lead':
        # Campaign leads can only update timesheets for their campaign
        if existing_timesheet.get('campaign_id') != g.campaign_id:
            return jsonify({'message': 'Access denied'}), 403
    
    # Prepare update data
    update_data = {}
    
    # Fields that can be updated
    allowed_fields = [
        'time_in', 'time_out', 
        'lunch_start', 'lunch_end', 
        'break1_start', 'break1_end', 
        'break2_start', 'break2_end',
        'vacation_type'
    ]
    
    for field in allowed_fields:
        if field in data:
            update_data[field] = data.get(field)
    
    # If no fields to update
    if not update_data:
        return jsonify({'message': 'No fields to update'}), 400
        
    # Merge existing data with update data for calculation
    calculation_data = {**existing_timesheet, **update_data}
    
    # Calculate total paid hours and unpaid breaks
    total_paid_hours, total_unpaid_breaks = calculate_hours(calculation_data)
    update_data['total_paid_hours'] = total_paid_hours
    update_data['total_unpaid_breaks'] = total_unpaid_breaks
        
    # Update timesheet
    response = supabase.table('timesheet_entries').update(update_data).eq('id', timesheet_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Failed to update timesheet entry'}), 500
        
    updated_timesheet = response.data[0]
    
    # Log timesheet update
    log_activity('timesheet_updated', 'timesheet_entries', timesheet_id)
    
    return jsonify(updated_timesheet)

@timesheets_bp.route('/<timesheet_id>/submit', methods=['PUT'])
@token_required
def submit_timesheet(timesheet_id):
    """
    Submit a timesheet entry for approval
    
    Path parameters:
        timesheet_id: ID of the timesheet entry to submit
        
    Returns:
        Updated timesheet entry information
    """
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check if timesheet exists
    response = supabase.table('timesheet_entries').select('*').eq('id', timesheet_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Timesheet entry not found'}), 404
        
    existing_timesheet = response.data[0]
    
    # Check permissions
    if g.user_role == 'team_member' and existing_timesheet.get('user_id') != g.user_id:
        return jsonify({'message': 'Access denied'}), 403
        
    if g.user_role == 'campaign_lead' and existing_timesheet.get('campaign_id') != g.campaign_id:
        return jsonify({'message': 'Access denied'}), 403
        
    # Check if timesheet is in draft or rejected status
    if existing_timesheet.get('status') not in ['draft', 'rejected']:
        return jsonify({'message': 'Timesheet must be in draft or rejected status to submit'}), 400
        
    # Update timesheet status
    update_data = {
        'status': 'pending',
        'submitted_at': datetime.utcnow().isoformat()
    }
        
    # Update timesheet
    response = supabase.table('timesheet_entries').update(update_data).eq('id', timesheet_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Failed to submit timesheet entry'}), 500
        
    updated_timesheet = response.data[0]
    
    # Get user and campaign lead information for email notification
    user_response = supabase.table('users').select('*').eq('id', updated_timesheet.get('user_id')).execute()
    
    if user_response.data and len(user_response.data) > 0:
        user = user_response.data[0]
        
        # Find campaign lead for this campaign
        campaign_lead_response = supabase.table('users').select('*').eq('campaign_id', updated_timesheet.get('campaign_id')).eq('role', 'campaign_lead').execute()
        
        if campaign_lead_response.data and len(campaign_lead_response.data) > 0:
            campaign_lead = campaign_lead_response.data[0]
            
            # Send email notification to campaign lead
            send_timesheet_submitted_notification(
                approver_email=campaign_lead.get('email'),
                submitter_name=user.get('full_name'),
                date=updated_timesheet.get('date'),
                timesheet_id=timesheet_id
            )
    
    # Log timesheet submission
    log_activity('timesheet_submitted', 'timesheet_entries', timesheet_id, {'status_change': f"{existing_timesheet.get('status')} -> pending"})
    
    return jsonify(updated_timesheet)

@timesheets_bp.route('/<timesheet_id>/approve', methods=['PUT'])
@token_required
@campaign_lead_required
def approve_timesheet(timesheet_id):
    """
    Approve a timesheet entry (campaign lead or admin only)
    
    Path parameters:
        timesheet_id: ID of the timesheet entry to approve
        
    Request body:
        {
            "comments": "Approved - all times look correct" (optional)
        }
        
    Returns:
        Updated timesheet entry information
    """
    data = request.json or {}
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check if timesheet exists
    response = supabase.table('timesheet_entries').select('*').eq('id', timesheet_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Timesheet entry not found'}), 404
        
    existing_timesheet = response.data[0]
    
    # Check permissions for campaign lead
    if g.user_role == 'campaign_lead' and existing_timesheet.get('campaign_id') != g.campaign_id:
        return jsonify({'message': 'Access denied'}), 403
        
    # Check if timesheet is in pending status
    if existing_timesheet.get('status') != 'pending':
        return jsonify({'message': 'Timesheet must be in pending status to approve'}), 400
        
    # Update timesheet status
    update_data = {
        'status': 'approved',
        'decision_at': datetime.utcnow().isoformat(),
        'approver_id': g.user_id
    }
    
    # Add comments if provided
    if data.get('comments'):
        update_data['approver_comments'] = data.get('comments')
        
    # Update timesheet
    response = supabase.table('timesheet_entries').update(update_data).eq('id', timesheet_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Failed to approve timesheet entry'}), 500
        
    updated_timesheet = response.data[0]
    
    # Get user and approver information for email notification
    user_response = supabase.table('users').select('*').eq('id', updated_timesheet.get('user_id')).execute()
    approver_response = supabase.table('users').select('*').eq('id', g.user_id).execute()
    
    if user_response.data and len(user_response.data) > 0 and approver_response.data and len(approver_response.data) > 0:
        user = user_response.data[0]
        approver = approver_response.data[0]
        
        # Send email notification to user
        send_timesheet_approved_notification(
            user_email=user.get('email'),
            approver_name=approver.get('full_name'),
            date=updated_timesheet.get('date'),
            timesheet_id=timesheet_id
        )
    
    # Log timesheet approval
    log_activity('timesheet_approved', 'timesheet_entries', timesheet_id, {
        'status_change': 'pending -> approved',
        'approver_comments': data.get('comments')
    })
    
    return jsonify(updated_timesheet)

@timesheets_bp.route('/<timesheet_id>/reject', methods=['PUT'])
@token_required
@campaign_lead_required
def reject_timesheet(timesheet_id):
    """
    Reject a timesheet entry (campaign lead or admin only)
    
    Path parameters:
        timesheet_id: ID of the timesheet entry to reject
        
    Request body:
        {
            "comments": "Rejected - lunch break is missing" (required)
        }
        
    Returns:
        Updated timesheet entry information
    """
    data = request.json or {}
    
    # Validate comments
    if not data.get('comments'):
        return jsonify({'message': 'Comments are required for rejection'}), 400
        
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check if timesheet exists
    response = supabase.table('timesheet_entries').select('*').eq('id', timesheet_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Timesheet entry not found'}), 404
        
    existing_timesheet = response.data[0]
    
    # Check permissions for campaign lead
    if g.user_role == 'campaign_lead' and existing_timesheet.get('campaign_id') != g.campaign_id:
        return jsonify({'message': 'Access denied'}), 403
        
    # Check if timesheet is in pending status
    if existing_timesheet.get('status') != 'pending':
        return jsonify({'message': 'Timesheet must be in pending status to reject'}), 400
        
    # Update timesheet status
    update_data = {
        'status': 'rejected',
        'decision_at': datetime.utcnow().isoformat(),
        'approver_id': g.user_id,
        'approver_comments': data.get('comments')
    }
        
    # Update timesheet
    response = supabase.table('timesheet_entries').update(update_data).eq('id', timesheet_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Failed to reject timesheet entry'}), 500
        
    updated_timesheet = response.data[0]
    
    # Get user and approver information for email notification
    user_response = supabase.table('users').select('*').eq('id', updated_timesheet.get('user_id')).execute()
    approver_response = supabase.table('users').select('*').eq('id', g.user_id).execute()
    
    if user_response.data and len(user_response.data) > 0 and approver_response.data and len(approver_response.data) > 0:
        user = user_response.data[0]
        approver = approver_response.data[0]
        
        # Send email notification to user
        send_timesheet_rejected_notification(
            user_email=user.get('email'),
            approver_name=approver.get('full_name'),
            date=updated_timesheet.get('date'),
            comments=data.get('comments'),
            timesheet_id=timesheet_id
        )
    
    # Log timesheet rejection
    log_activity('timesheet_rejected', 'timesheet_entries', timesheet_id, {
        'status_change': 'pending -> rejected',
        'approver_comments': data.get('comments')
    })
    
    return jsonify(updated_timesheet)

@timesheets_bp.route('/<timesheet_id>', methods=['DELETE'])
@token_required
def delete_timesheet(timesheet_id):
    """
    Delete a timesheet entry
    
    Path parameters:
        timesheet_id: ID of the timesheet entry to delete
        
    Returns:
        Success message
    """
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check if timesheet exists
    response = supabase.table('timesheet_entries').select('*').eq('id', timesheet_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Timesheet entry not found'}), 404
        
    existing_timesheet = response.data[0]
    
    # Check permissions
    if g.user_role == 'team_member':
        # Team members can only delete their own draft timesheets
        if existing_timesheet.get('user_id') != g.user_id:
            return jsonify({'message': 'Access denied'}), 403
            
        if existing_timesheet.get('status') != 'draft':
            return jsonify({'message': 'Can only delete timesheets in draft status'}), 400
    elif g.user_role == 'campaign_lead':
        # Campaign leads can only delete timesheets for their campaign
        if existing_timesheet.get('campaign_id') != g.campaign_id:
            return jsonify({'message': 'Access denied'}), 403
    
    # Delete timesheet
    response = supabase.table('timesheet_entries').delete().eq('id', timesheet_id).execute()
    
    # Log timesheet deletion
    log_activity('timesheet_deleted', 'timesheet_entries', timesheet_id)
    
    return jsonify({'message': 'Timesheet entry deleted successfully'}), 200

