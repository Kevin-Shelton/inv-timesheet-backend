from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
import calendar
from src.utils.supabase import get_supabase_client
from src.middleware.auth import token_required, admin_required, campaign_lead_required, log_activity

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/campaign-summary', methods=['GET'])
@token_required
@campaign_lead_required
def campaign_summary():
    """
    Generate a campaign summary report
    
    Query parameters:
        campaign_id (required for admin): ID of the campaign to report on
        month (required): Month to report on (YYYY-MM)
        
    Returns:
        Campaign summary report data
    """
    # Get query parameters
    campaign_id = request.args.get('campaign_id')
    month = request.args.get('month')
    
    # Validate month parameter
    if not month or not month.match(r'^\d{4}-\d{2}$'):
        return jsonify({'message': 'month parameter is required in format YYYY-MM'}), 400
        
    # Determine campaign_id based on role
    if g.user_role == 'admin':
        if not campaign_id:
            return jsonify({'message': 'campaign_id parameter is required for admin users'}), 400
    else:
        # Campaign leads use their assigned campaign
        campaign_id = g.campaign_id
        
    # Parse month parameter
    year, month_num = map(int, month.split('-'))
    
    # Calculate start and end dates for the month
    start_date = f"{year}-{month_num:02d}-01"
    _, last_day = calendar.monthrange(year, month_num)
    end_date = f"{year}-{month_num:02d}-{last_day}"
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Get campaign details
    campaign_response = supabase.table('campaigns').select('*').eq('id', campaign_id).execute()
    
    if not campaign_response.data or len(campaign_response.data) == 0:
        return jsonify({'message': 'Campaign not found'}), 404
        
    campaign = campaign_response.data[0]
    
    # Get all users in the campaign
    users_response = supabase.table('users').select('*').eq('campaign_id', campaign_id).execute()
    
    if not users_response.data:
        return jsonify({'message': 'No users found in this campaign'}), 404
        
    users = users_response.data
    
    # Get all timesheet entries for the campaign in the specified month
    timesheets_response = supabase.table('timesheet_entries') \
        .select('*') \
        .eq('campaign_id', campaign_id) \
        .gte('date', start_date) \
        .lte('date', end_date) \
        .execute()
        
    timesheets = timesheets_response.data or []
    
    # Get schedule for the campaign
    schedules_response = supabase.table('schedules').select('*').eq('campaign_id', campaign_id).execute()
    schedules = schedules_response.data or []
    
    # Default schedule hours (8 hours per day)
    default_work_hours = 8.0
    
    # If schedule exists, calculate scheduled hours
    if schedules:
        schedule = schedules[0]
        work_start = datetime.strptime(schedule.get('work_start_time'), '%H:%M:%S')
        work_end = datetime.strptime(schedule.get('work_end_time'), '%H:%M:%S')
        lunch_duration = schedule.get('lunch_duration_minutes', 60) / 60  # Convert to hours
        
        # Calculate scheduled hours per day
        default_work_hours = (work_end - work_start).total_seconds() / 3600 - lunch_duration
    
    # Calculate working days in the month (excluding weekends)
    working_days = 0
    current_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
    
    while current_date <= end_datetime:
        if current_date.weekday() < 5:  # Monday to Friday
            working_days += 1
        current_date += timedelta(days=1)
    
    # Calculate scheduled hours for the month
    scheduled_hours_per_month = working_days * default_work_hours
    
    # Initialize summary data
    summary = {
        'campaign': campaign,
        'period': {
            'month': month,
            'start_date': start_date,
            'end_date': end_date,
            'working_days': working_days,
            'scheduled_hours_per_day': default_work_hours,
            'scheduled_hours_per_month': scheduled_hours_per_month
        },
        'totals': {
            'total_worked_hours': 0,
            'total_billable_hours': 0,
            'total_payroll_cost': 0,
            'total_billable_amount': 0,
            'total_variance': 0
        },
        'users': [],
        'absence_summary': {
            'vacation': 0,
            'sick': 0,
            'holiday': 0,
            'personal': 0,
            'worked': 0
        }
    }
    
    # Process each user
    for user in users:
        user_timesheets = [t for t in timesheets if t.get('user_id') == user.get('id')]
        
        # Calculate user metrics
        worked_hours = sum(t.get('total_paid_hours', 0) for t in user_timesheets if t.get('status') == 'approved')
        billable_hours = worked_hours  # Billable hours are the same as worked hours in this case
        
        # Calculate costs and revenue
        pay_rate = user.get('pay_rate_per_hour', 0)
        billing_rate = campaign.get('billing_rate_per_hour', 0)
        
        payroll_cost = worked_hours * pay_rate
        billable_amount = billable_hours * billing_rate
        variance = billable_amount - payroll_cost
        
        # Count absence types
        absence_counts = {
            'vacation': 0,
            'sick': 0,
            'holiday': 0,
            'personal': 0
        }
        
        for t in user_timesheets:
            if t.get('vacation_type') != 'none' and t.get('status') == 'approved':
                absence_counts[t.get('vacation_type')] += 1
        
        # Calculate worked days
        worked_days = len([t for t in user_timesheets if t.get('vacation_type') == 'none' and t.get('status') == 'approved'])
        
        # Add user summary to the list
        user_summary = {
            'id': user.get('id'),
            'full_name': user.get('full_name'),
            'email': user.get('email'),
            'pay_rate': pay_rate,
            'scheduled_hours': scheduled_hours_per_month,
            'worked_hours': worked_hours,
            'billable_hours': billable_hours,
            'payroll_cost': payroll_cost,
            'billable_amount': billable_amount,
            'variance': variance,
            'absence_days': absence_counts,
            'worked_days': worked_days
        }
        
        summary['users'].append(user_summary)
        
        # Update totals
        summary['totals']['total_worked_hours'] += worked_hours
        summary['totals']['total_billable_hours'] += billable_hours
        summary['totals']['total_payroll_cost'] += payroll_cost
        summary['totals']['total_billable_amount'] += billable_amount
        summary['totals']['total_variance'] += variance
        
        # Update absence summary
        for absence_type, count in absence_counts.items():
            summary['absence_summary'][absence_type] += count
            
        summary['absence_summary']['worked'] += worked_days
    
    # Log report generation
    log_activity('report_generated', 'campaigns', campaign_id, {'report_type': 'campaign_summary', 'month': month})
    
    return jsonify(summary)

@reports_bp.route('/organization-summary', methods=['GET'])
@token_required
@admin_required
def organization_summary():
    """
    Generate an organization-wide summary report (admin only)
    
    Query parameters:
        month (required): Month to report on (YYYY-MM)
        
    Returns:
        Organization summary report data
    """
    # Get query parameters
    month = request.args.get('month')
    
    # Validate month parameter
    if not month or not month.match(r'^\d{4}-\d{2}$'):
        return jsonify({'message': 'month parameter is required in format YYYY-MM'}), 400
        
    # Parse month parameter
    year, month_num = map(int, month.split('-'))
    
    # Calculate start and end dates for the month
    start_date = f"{year}-{month_num:02d}-01"
    _, last_day = calendar.monthrange(year, month_num)
    end_date = f"{year}-{month_num:02d}-{last_day}"
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Get all campaigns
    campaigns_response = supabase.table('campaigns').select('*').execute()
    
    if not campaigns_response.data:
        return jsonify({'message': 'No campaigns found'}), 404
        
    campaigns = campaigns_response.data
    
    # Initialize organization summary
    org_summary = {
        'period': {
            'month': month,
            'start_date': start_date,
            'end_date': end_date
        },
        'totals': {
            'total_worked_hours': 0,
            'total_billable_hours': 0,
            'total_payroll_cost': 0,
            'total_billable_amount': 0,
            'total_variance': 0
        },
        'campaigns': [],
        'absence_summary': {
            'vacation': 0,
            'sick': 0,
            'holiday': 0,
            'personal': 0,
            'worked': 0
        }
    }
    
    # Process each campaign
    for campaign in campaigns:
        # Get campaign summary using the existing endpoint
        campaign_summary_response = campaign_summary(campaign_id=campaign.get('id'), month=month)
        campaign_summary_data = campaign_summary_response.json
        
        # Add campaign summary to the list
        org_summary['campaigns'].append({
            'id': campaign.get('id'),
            'name': campaign.get('name'),
            'billing_rate': campaign.get('billing_rate_per_hour'),
            'worked_hours': campaign_summary_data['totals']['total_worked_hours'],
            'billable_hours': campaign_summary_data['totals']['total_billable_hours'],
            'payroll_cost': campaign_summary_data['totals']['total_payroll_cost'],
            'billable_amount': campaign_summary_data['totals']['total_billable_amount'],
            'variance': campaign_summary_data['totals']['total_variance'],
            'user_count': len(campaign_summary_data['users'])
        })
        
        # Update organization totals
        org_summary['totals']['total_worked_hours'] += campaign_summary_data['totals']['total_worked_hours']
        org_summary['totals']['total_billable_hours'] += campaign_summary_data['totals']['total_billable_hours']
        org_summary['totals']['total_payroll_cost'] += campaign_summary_data['totals']['total_payroll_cost']
        org_summary['totals']['total_billable_amount'] += campaign_summary_data['totals']['total_billable_amount']
        org_summary['totals']['total_variance'] += campaign_summary_data['totals']['total_variance']
        
        # Update absence summary
        for absence_type in ['vacation', 'sick', 'holiday', 'personal', 'worked']:
            org_summary['absence_summary'][absence_type] += campaign_summary_data['absence_summary'][absence_type]
    
    # Log report generation
    log_activity('report_generated', None, None, {'report_type': 'organization_summary', 'month': month})
    
    return jsonify(org_summary)

@reports_bp.route('/user-timesheet', methods=['GET'])
@token_required
def user_timesheet_report():
    """
    Generate a timesheet report for a specific user
    
    Query parameters:
        user_id (required for admin/lead): ID of the user to report on
        month (required): Month to report on (YYYY-MM)
        
    Returns:
        User timesheet report data
    """
    # Get query parameters
    user_id = request.args.get('user_id')
    month = request.args.get('month')
    
    # Validate month parameter
    if not month or not month.match(r'^\d{4}-\d{2}$'):
        return jsonify({'message': 'month parameter is required in format YYYY-MM'}), 400
        
    # Determine user_id based on role
    if g.user_role == 'team_member':
        # Team members can only see their own timesheets
        user_id = g.user_id
    elif g.user_role != 'admin' and not user_id:
        # Campaign leads need to specify user_id
        return jsonify({'message': 'user_id parameter is required'}), 400
        
    # Parse month parameter
    year, month_num = map(int, month.split('-'))
    
    # Calculate start and end dates for the month
    start_date = f"{year}-{month_num:02d}-01"
    _, last_day = calendar.monthrange(year, month_num)
    end_date = f"{year}-{month_num:02d}-{last_day}"
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Get user details
    user_response = supabase.table('users').select('*').eq('id', user_id).execute()
    
    if not user_response.data or len(user_response.data) == 0:
        return jsonify({'message': 'User not found'}), 404
        
    user = user_response.data[0]
    
    # Check permissions for campaign lead
    if g.user_role == 'campaign_lead' and user.get('campaign_id') != g.campaign_id:
        return jsonify({'message': 'Access denied'}), 403
        
    # Get all timesheet entries for the user in the specified month
    timesheets_response = supabase.table('timesheet_entries') \
        .select('*') \
        .eq('user_id', user_id) \
        .gte('date', start_date) \
        .lte('date', end_date) \
        .order('date') \
        .execute()
        
    timesheets = timesheets_response.data or []
    
    # Get campaign details
    campaign_id = user.get('campaign_id')
    campaign = None
    
    if campaign_id:
        campaign_response = supabase.table('campaigns').select('*').eq('id', campaign_id).execute()
        if campaign_response.data and len(campaign_response.data) > 0:
            campaign = campaign_response.data[0]
    
    # Initialize report data
    report = {
        'user': {
            'id': user.get('id'),
            'full_name': user.get('full_name'),
            'email': user.get('email'),
            'pay_rate': user.get('pay_rate_per_hour')
        },
        'campaign': campaign,
        'period': {
            'month': month,
            'start_date': start_date,
            'end_date': end_date
        },
        'timesheets': timesheets,
        'summary': {
            'total_days': len(timesheets),
            'approved_days': len([t for t in timesheets if t.get('status') == 'approved']),
            'pending_days': len([t for t in timesheets if t.get('status') == 'pending']),
            'rejected_days': len([t for t in timesheets if t.get('status') == 'rejected']),
            'draft_days': len([t for t in timesheets if t.get('status') == 'draft']),
            'total_worked_hours': sum(t.get('total_paid_hours', 0) for t in timesheets if t.get('status') == 'approved'),
            'total_break_hours': sum(t.get('total_unpaid_breaks', 0) for t in timesheets if t.get('status') == 'approved'),
            'absence_days': {
                'vacation': len([t for t in timesheets if t.get('vacation_type') == 'vacation' and t.get('status') == 'approved']),
                'sick': len([t for t in timesheets if t.get('vacation_type') == 'sick' and t.get('status') == 'approved']),
                'holiday': len([t for t in timesheets if t.get('vacation_type') == 'holiday' and t.get('status') == 'approved']),
                'personal': len([t for t in timesheets if t.get('vacation_type') == 'personal' and t.get('status') == 'approved'])
            }
        }
    }
    
    # Calculate payroll and billing
    if campaign:
        report['summary']['payroll_amount'] = report['summary']['total_worked_hours'] * user.get('pay_rate_per_hour', 0)
        report['summary']['billable_amount'] = report['summary']['total_worked_hours'] * campaign.get('billing_rate_per_hour', 0)
        report['summary']['variance'] = report['summary']['billable_amount'] - report['summary']['payroll_amount']
    
    # Log report generation
    log_activity('report_generated', 'users', user_id, {'report_type': 'user_timesheet', 'month': month})
    
    return jsonify(report)

@reports_bp.route('/export-csv', methods=['GET'])
@token_required
def export_csv():
    """
    Export report data as CSV
    
    Query parameters:
        report_type (required): Type of report to export (campaign-summary, organization-summary, user-timesheet)
        campaign_id (required for campaign-summary): ID of the campaign to report on
        user_id (required for user-timesheet): ID of the user to report on
        month (required): Month to report on (YYYY-MM)
        
    Returns:
        CSV data as text/csv
    """
    # This endpoint would generate CSV data based on the report type
    # For now, we'll return a placeholder message
    return jsonify({'message': 'CSV export functionality will be implemented in the frontend'}), 501

@reports_bp.route('/export-pdf', methods=['GET'])
@token_required
def export_pdf():
    """
    Export report data as PDF
    
    Query parameters:
        report_type (required): Type of report to export (campaign-summary, organization-summary, user-timesheet)
        campaign_id (required for campaign-summary): ID of the campaign to report on
        user_id (required for user-timesheet): ID of the user to report on
        month (required): Month to report on (YYYY-MM)
        
    Returns:
        PDF data as application/pdf
    """
    # This endpoint would generate PDF data based on the report type
    # For now, we'll return a placeholder message
    return jsonify({'message': 'PDF export functionality will be implemented in the frontend'}), 501

