from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import uuid
from src.utils.supabase import get_supabase_client

# Create blueprint
task_timesheet_bp = Blueprint('task_timesheet', __name__)

# Utility functions
def get_supabase():
    """Get Supabase client"""
    return get_supabase_client()

def format_response(data=None, message="Success", status="success"):
    """Format API response"""
    response = {
        "status": status,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return response

def validate_duration(hours, minutes):
    """Validate duration format"""
    try:
        hours = int(hours)
        minutes = int(minutes)
        return 0 <= hours <= 23 and 0 <= minutes <= 59
    except (ValueError, TypeError):
        return False

# Routes

@task_timesheet_bp.route('/campaigns', methods=['GET'])
def get_campaigns():
    """Get available campaigns for task timesheet"""
    try:
        supabase = get_supabase()
        user_id = request.args.get('user_id')
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        query = supabase.table('campaigns').select('*')
        
        if not include_inactive:
            query = query.eq('is_active', True)
        
        result = query.execute()
        
        campaigns = []
        for campaign in result.data:
            campaigns.append({
                'id': campaign['id'],
                'name': campaign['name'],
                'client_name': campaign.get('client_name', ''),
                'description': campaign.get('description', ''),
                'is_billable': campaign.get('is_billable', True),
                'hourly_rate': float(campaign.get('billing_rate_per_hour', 0)),
                'is_active': campaign.get('is_active', True)
            })
        
        return jsonify(format_response(campaigns))
        
    except Exception as e:
        return jsonify(format_response(
            message=f"Error fetching campaigns: {str(e)}",
            status="error"
        )), 500

@task_timesheet_bp.route('/campaigns/<campaign_id>/tasks', methods=['GET'])
def get_campaign_tasks(campaign_id):
    """Get task templates for a specific campaign"""
    try:
        supabase = get_supabase()
        
        result = supabase.table('task_templates').select('*').eq('campaign_id', campaign_id).execute()
        
        tasks = []
        for task in result.data:
            tasks.append({
                'id': task['id'],
                'task_name': task['task_name'],
                'description': task.get('description', ''),
                'is_default': task.get('is_default', False),
                'is_billable': task.get('is_billable', True)
            })
        
        return jsonify(format_response(tasks))
        
    except Exception as e:
        return jsonify(format_response(
            message=f"Error fetching task templates: {str(e)}",
            status="error"
        )), 500

@task_timesheet_bp.route('/system/settings', methods=['GET'])
def get_system_settings():
    """Get system settings for OT calculation"""
    try:
        supabase = get_supabase()
        
        result = supabase.table('system_config').select('*').execute()
        
        settings = {
            'regular_hours_threshold': 40,
            'overtime_multiplier': 1.5,
            'max_daily_hours': 12,
            'min_break_duration': 30,
            'default_week_start': 'monday'
        }
        
        # Override with database values if they exist
        for config in result.data:
            key = config.get('config_key')
            value = config.get('config_value')
            if key in settings:
                try:
                    if key in ['regular_hours_threshold', 'max_daily_hours', 'min_break_duration']:
                        settings[key] = int(value)
                    elif key == 'overtime_multiplier':
                        settings[key] = float(value)
                    else:
                        settings[key] = value
                except (ValueError, TypeError):
                    pass  # Keep default value
        
        return jsonify(format_response(settings))
        
    except Exception as e:
        return jsonify(format_response(
            message=f"Error fetching system settings: {str(e)}",
            status="error"
        )), 500

@task_timesheet_bp.route('/create', methods=['POST'])
def create_task_timesheet():
    """Create a new task timesheet entry"""
    try:
        data = request.get_json()
        supabase = get_supabase()
        
        # Validate required fields
        required_fields = ['user_id', 'campaign_id', 'task_name', 'week_start_date']
        for field in required_fields:
            if field not in data:
                return jsonify(format_response(
                    message=f"Missing required field: {field}",
                    status="error"
                )), 400
        
        # Create timesheet entry
        timesheet_data = {
            'id': str(uuid.uuid4()),
            'user_id': data['user_id'],
            'campaign_id': data['campaign_id'],
            'task_template_id': data.get('task_template_id'),
            'custom_task_name': data.get('custom_task_name'),
            'task_name': data['task_name'],
            'task_description': data.get('task_description', ''),
            'week_start_date': data['week_start_date'],
            'week_end_date': data.get('week_end_date'),
            'status': 'draft',
            'notes': data.get('notes', ''),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        result = supabase.table('task_timesheets').insert(timesheet_data).execute()
        
        return jsonify(format_response(
            result.data[0] if result.data else timesheet_data,
            "Task timesheet created successfully"
        )), 201
        
    except Exception as e:
        return jsonify(format_response(
            message=f"Error creating task timesheet: {str(e)}",
            status="error"
        )), 500

@task_timesheet_bp.route('/<timesheet_id>/entries', methods=['PUT'])
def update_time_entry(timesheet_id):
    """Update time entry for a task"""
    try:
        data = request.get_json()
        supabase = get_supabase()
        
        # Validate required fields
        required_fields = ['entry_date', 'duration_hours', 'duration_minutes', 'is_completed']
        for field in required_fields:
            if field not in data:
                return jsonify(format_response(
                    message=f"Missing required field: {field}",
                    status="error"
                )), 400
        
        # Validate duration format
        hours = data['duration_hours']
        minutes = data['duration_minutes']
        
        if not validate_duration(hours, minutes):
            return jsonify(format_response(
                message="Invalid duration format. Hours must be 0-23, minutes must be 0-59",
                status="error"
            )), 400
        
        # Check if entry exists
        existing_result = supabase.table('task_time_entries').select('*').eq('task_timesheet_id', timesheet_id).eq('entry_date', data['entry_date']).execute()
        
        entry_data = {
            'task_timesheet_id': timesheet_id,
            'entry_date': data['entry_date'],
            'duration_hours': int(hours),
            'duration_minutes': int(minutes),
            'is_completed': data['is_completed'],
            'notes': data.get('notes', ''),
            'updated_at': datetime.now().isoformat()
        }
        
        if existing_result.data:
            # Update existing entry
            result = supabase.table('task_time_entries').update(entry_data).eq('id', existing_result.data[0]['id']).execute()
        else:
            # Create new entry
            entry_data['id'] = str(uuid.uuid4())
            entry_data['created_at'] = datetime.now().isoformat()
            result = supabase.table('task_time_entries').insert(entry_data).execute()
        
        return jsonify(format_response(
            result.data[0] if result.data else entry_data,
            "Time entry updated successfully"
        ))
        
    except Exception as e:
        return jsonify(format_response(
            message=f"Error updating time entry: {str(e)}",
            status="error"
        )), 500

@task_timesheet_bp.route('/week/<user_id>/<week_start>', methods=['GET'])
def get_user_week_timesheet(user_id, week_start):
    """Get user's task timesheet for a specific week"""
    try:
        supabase = get_supabase()
        
        # Validate date format
        try:
            week_start_date = datetime.strptime(week_start, "%Y-%m-%d")
            week_end_date = week_start_date + timedelta(days=6)
        except ValueError:
            return jsonify(format_response(
                message="Invalid date format. Use YYYY-MM-DD",
                status="error"
            )), 400
        
        # Get timesheets for the week
        timesheets_result = supabase.table('task_timesheets').select('*').eq('user_id', user_id).eq('week_start_date', week_start).execute()
        
        # Get time entries for all timesheets
        timesheet_ids = [ts['id'] for ts in timesheets_result.data]
        time_entries = []
        
        if timesheet_ids:
            entries_result = supabase.table('task_time_entries').select('*').in_('task_timesheet_id', timesheet_ids).execute()
            time_entries = entries_result.data
        
        # Get campaign information
        campaign_ids = list(set([ts['campaign_id'] for ts in timesheets_result.data]))
        campaigns = {}
        
        if campaign_ids:
            campaigns_result = supabase.table('campaigns').select('*').in_('id', campaign_ids).execute()
            campaigns = {c['id']: c for c in campaigns_result.data}
        
        # Build response
        tasks = []
        daily_totals = {}
        weekly_total_minutes = 0
        
        for timesheet in timesheets_result.data:
            campaign = campaigns.get(timesheet['campaign_id'], {})
            
            # Get time entries for this timesheet
            task_entries = [e for e in time_entries if e['task_timesheet_id'] == timesheet['id']]
            
            # Build time entries by date
            time_entries_by_date = {}
            task_total_minutes = 0
            
            for entry in task_entries:
                date = entry['entry_date']
                duration_minutes = entry['duration_hours'] * 60 + entry['duration_minutes']
                
                time_entries_by_date[date] = {
                    'duration_hours': entry['duration_hours'],
                    'duration_minutes': entry['duration_minutes'],
                    'is_completed': entry['is_completed'],
                    'notes': entry.get('notes', '')
                }
                
                task_total_minutes += duration_minutes
                
                # Add to daily totals
                if date not in daily_totals:
                    daily_totals[date] = 0
                daily_totals[date] += duration_minutes
            
            weekly_total_minutes += task_total_minutes
            
            tasks.append({
                'id': timesheet['id'],
                'campaign_name': campaign.get('name', 'Unknown Campaign'),
                'task_name': timesheet['task_name'],
                'task_description': timesheet.get('task_description', ''),
                'is_billable': campaign.get('is_billable', True),
                'hourly_rate': float(campaign.get('billing_rate_per_hour', 0)),
                'time_entries': time_entries_by_date,
                'task_total_hours': task_total_minutes // 60,
                'task_total_minutes': task_total_minutes % 60,
                'notes': timesheet.get('notes', '')
            })
        
        # Convert daily totals to hours and minutes
        daily_totals_formatted = {}
        for date, minutes in daily_totals.items():
            daily_totals_formatted[date] = {
                'hours': minutes // 60,
                'minutes': minutes % 60
            }
        
        # Calculate overtime
        settings_result = supabase.table('system_config').select('*').eq('config_key', 'regular_hours_threshold').execute()
        threshold_hours = 40
        if settings_result.data:
            try:
                threshold_hours = int(settings_result.data[0]['config_value'])
            except (ValueError, TypeError):
                pass
        
        weekly_total_hours = weekly_total_minutes // 60
        weekly_total_mins = weekly_total_minutes % 60
        
        if weekly_total_hours > threshold_hours:
            overtime_hours = weekly_total_hours - threshold_hours
            regular_hours = threshold_hours
            regular_minutes = 0
            overtime_minutes = weekly_total_mins
        else:
            overtime_hours = 0
            overtime_minutes = 0
            regular_hours = weekly_total_hours
            regular_minutes = weekly_total_mins
        
        response_data = {
            'user_id': user_id,
            'week_start_date': week_start,
            'week_end_date': week_end_date.strftime('%Y-%m-%d'),
            'tasks': tasks,
            'daily_totals': daily_totals_formatted,
            'weekly_total': {
                'hours': weekly_total_hours,
                'minutes': weekly_total_mins
            },
            'regular_hours': {
                'hours': regular_hours,
                'minutes': regular_minutes
            },
            'overtime_hours': {
                'hours': overtime_hours,
                'minutes': overtime_minutes
            }
        }
        
        return jsonify(format_response(response_data))
        
    except Exception as e:
        return jsonify(format_response(
            message=f"Error fetching week timesheet: {str(e)}",
            status="error"
        )), 500

@task_timesheet_bp.route('/submit', methods=['POST'])
def submit_timesheet():
    """Submit timesheet for approval"""
    try:
        data = request.get_json()
        supabase = get_supabase()
        
        user_id = data.get('user_id')
        week_start = data.get('week_start_date')
        
        if not user_id or not week_start:
            return jsonify(format_response(
                message="User ID and week start date are required",
                status="error"
            )), 400
        
        # Update all timesheets for the week to submitted status
        result = supabase.table('task_timesheets').update({
            'status': 'submitted',
            'submitted_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }).eq('user_id', user_id).eq('week_start_date', week_start).execute()
        
        return jsonify(format_response(
            {
                'submission_id': str(uuid.uuid4()),
                'submitted_at': datetime.now().isoformat(),
                'timesheets_updated': len(result.data) if result.data else 0
            },
            "Timesheet submitted for approval successfully"
        ))
        
    except Exception as e:
        return jsonify(format_response(
            message=f"Error submitting timesheet: {str(e)}",
            status="error"
        )), 500

@task_timesheet_bp.route('/approve', methods=['POST'])
def approve_timesheet():
    """Approve timesheet (for managers)"""
    try:
        data = request.get_json()
        supabase = get_supabase()
        
        timesheet_id = data.get('timesheet_id')
        approver_id = data.get('approver_id')
        comments = data.get('comments', '')
        
        if not timesheet_id or not approver_id:
            return jsonify(format_response(
                message="Timesheet ID and approver ID are required",
                status="error"
            )), 400
        
        # Update timesheet status
        result = supabase.table('task_timesheets').update({
            'status': 'approved',
            'approved_by': approver_id,
            'approved_at': datetime.now().isoformat(),
            'approval_comments': comments,
            'updated_at': datetime.now().isoformat()
        }).eq('id', timesheet_id).execute()
        
        return jsonify(format_response(
            {
                'approved_at': datetime.now().isoformat(),
                'approved_by': approver_id,
                'comments': comments
            },
            "Timesheet approved successfully"
        ))
        
    except Exception as e:
        return jsonify(format_response(
            message=f"Error approving timesheet: {str(e)}",
            status="error"
        )), 500

@task_timesheet_bp.route('/reject', methods=['POST'])
def reject_timesheet():
    """Reject timesheet (for managers)"""
    try:
        data = request.get_json()
        supabase = get_supabase()
        
        timesheet_id = data.get('timesheet_id')
        approver_id = data.get('approver_id')
        comments = data.get('comments', '')
        
        if not timesheet_id or not approver_id:
            return jsonify(format_response(
                message="Timesheet ID and approver ID are required",
                status="error"
            )), 400
        
        if not comments:
            return jsonify(format_response(
                message="Comments are required for rejection",
                status="error"
            )), 400
        
        # Update timesheet status
        result = supabase.table('task_timesheets').update({
            'status': 'rejected',
            'approved_by': approver_id,
            'approved_at': datetime.now().isoformat(),
            'approval_comments': comments,
            'updated_at': datetime.now().isoformat()
        }).eq('id', timesheet_id).execute()
        
        return jsonify(format_response(
            {
                'rejected_at': datetime.now().isoformat(),
                'rejected_by': approver_id,
                'comments': comments
            },
            "Timesheet rejected"
        ))
        
    except Exception as e:
        return jsonify(format_response(
            message=f"Error rejecting timesheet: {str(e)}",
            status="error"
        )), 500

@task_timesheet_bp.route('/billable-hours/create', methods=['POST'])
def create_billable_from_timesheet():
    """Create billable hours entries from approved timesheets"""
    try:
        data = request.get_json()
        supabase = get_supabase()
        
        timesheet_id = data.get('timesheet_id')
        
        if not timesheet_id:
            return jsonify(format_response(
                message="Timesheet ID is required",
                status="error"
            )), 400
        
        # Get timesheet details
        timesheet_result = supabase.table('task_timesheets').select('*').eq('id', timesheet_id).eq('status', 'approved').execute()
        
        if not timesheet_result.data:
            return jsonify(format_response(
                message="Approved timesheet not found",
                status="error"
            )), 404
        
        timesheet = timesheet_result.data[0]
        
        # Get time entries
        entries_result = supabase.table('task_time_entries').select('*').eq('task_timesheet_id', timesheet_id).execute()
        
        # Get campaign details
        campaign_result = supabase.table('campaigns').select('*').eq('id', timesheet['campaign_id']).execute()
        
        if not campaign_result.data:
            return jsonify(format_response(
                message="Campaign not found",
                status="error"
            )), 404
        
        campaign = campaign_result.data[0]
        
        # Calculate total billable hours and amount
        total_minutes = 0
        for entry in entries_result.data:
            total_minutes += entry['duration_hours'] * 60 + entry['duration_minutes']
        
        total_hours = total_minutes / 60
        hourly_rate = float(campaign.get('billing_rate_per_hour', 0))
        total_amount = total_hours * hourly_rate
        
        # Create billable hours entry (mock implementation)
        billable_entry = {
            'id': str(uuid.uuid4()),
            'user_id': timesheet['user_id'],
            'campaign_id': timesheet['campaign_id'],
            'task_timesheet_id': timesheet_id,
            'hours': total_hours,
            'hourly_rate': hourly_rate,
            'total_amount': total_amount,
            'created_at': datetime.now().isoformat()
        }
        
        return jsonify(format_response(
            {
                'billable_entry': billable_entry,
                'total_billable_hours': total_hours,
                'total_amount': total_amount
            },
            "Billable hours created from timesheet successfully"
        ))
        
    except Exception as e:
        return jsonify(format_response(
            message=f"Error creating billable hours: {str(e)}",
            status="error"
        )), 500

