from flask import Blueprint, request, jsonify, g
from src.utils.supabase import get_supabase_client
from src.middleware.auth import token_required, admin_required, campaign_lead_required, log_activity

campaigns_bp = Blueprint('campaigns', __name__)

@campaigns_bp.route('', methods=['GET'])
@token_required
def get_campaigns():
    """
    Get campaigns based on role:
    - Admin: All campaigns
    - Campaign Lead: Only their assigned campaign
    - Team Member: Only their assigned campaign
    
    Returns:
        List of campaigns
    """
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Start building query
    query = supabase.table('campaigns').select('*')
    
    # Apply role-based filtering
    if g.user_role != 'admin':
        # Non-admin users can only see their assigned campaign
        query = query.eq('id', g.campaign_id)
        
    # Execute query
    response = query.execute()
    
    return jsonify(response.data)

@campaigns_bp.route('/<campaign_id>', methods=['GET'])
@token_required
def get_campaign(campaign_id):
    """
    Get a specific campaign
    
    Path parameters:
        campaign_id: ID of the campaign to retrieve
        
    Returns:
        Campaign information
    """
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check permissions for non-admin users
    if g.user_role != 'admin' and g.campaign_id != campaign_id:
        return jsonify({'message': 'Access denied'}), 403
    
    # Query campaign
    response = supabase.table('campaigns').select('*').eq('id', campaign_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Campaign not found'}), 404
        
    return jsonify(response.data[0])

@campaigns_bp.route('', methods=['POST'])
@token_required
@admin_required
def create_campaign():
    """
    Create a new campaign (admin only)
    
    Request body:
        {
            "name": "New Campaign",
            "billing_rate_per_hour": 30.00
        }
        
    Returns:
        Created campaign information
    """
    data = request.json
    
    # Validate required fields
    required_fields = ['name', 'billing_rate_per_hour']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'message': f'{field} is required'}), 400
            
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check if campaign name already exists
    response = supabase.table('campaigns').select('id').eq('name', data.get('name')).execute()
    if response.data and len(response.data) > 0:
        return jsonify({'message': 'Campaign name already exists'}), 409
        
    # Prepare campaign data
    campaign_data = {
        'name': data.get('name'),
        'billing_rate_per_hour': data.get('billing_rate_per_hour')
    }
        
    # Insert campaign
    response = supabase.table('campaigns').insert(campaign_data).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Failed to create campaign'}), 500
        
    created_campaign = response.data[0]
    
    # Log campaign creation
    log_activity('campaign_created', 'campaigns', created_campaign.get('id'))
    
    return jsonify(created_campaign), 201

@campaigns_bp.route('/<campaign_id>', methods=['PUT'])
@token_required
@admin_required
def update_campaign(campaign_id):
    """
    Update a campaign (admin only)
    
    Path parameters:
        campaign_id: ID of the campaign to update
        
    Request body:
        {
            "name": "Updated Campaign Name",
            "billing_rate_per_hour": 35.00
        }
        
    Returns:
        Updated campaign information
    """
    data = request.json
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check if campaign exists
    response = supabase.table('campaigns').select('*').eq('id', campaign_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Campaign not found'}), 404
        
    # Prepare update data
    update_data = {}
    
    allowed_fields = ['name', 'billing_rate_per_hour']
    for field in allowed_fields:
        if field in data:
            update_data[field] = data.get(field)
    
    # If no fields to update
    if not update_data:
        return jsonify({'message': 'No fields to update'}), 400
        
    # If updating name, check if new name already exists
    if 'name' in update_data:
        response = supabase.table('campaigns').select('id').eq('name', update_data['name']).neq('id', campaign_id).execute()
        if response.data and len(response.data) > 0:
            return jsonify({'message': 'Campaign name already exists'}), 409
        
    # Update campaign
    response = supabase.table('campaigns').update(update_data).eq('id', campaign_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Failed to update campaign'}), 500
        
    updated_campaign = response.data[0]
    
    # Log campaign update
    log_activity('campaign_updated', 'campaigns', campaign_id)
    
    return jsonify(updated_campaign)

@campaigns_bp.route('/<campaign_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_campaign(campaign_id):
    """
    Delete a campaign (admin only)
    
    Path parameters:
        campaign_id: ID of the campaign to delete
        
    Returns:
        Success message
    """
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Check if campaign exists
    response = supabase.table('campaigns').select('id').eq('id', campaign_id).execute()
    
    if not response.data or len(response.data) == 0:
        return jsonify({'message': 'Campaign not found'}), 404
        
    # Check if campaign has users assigned
    response = supabase.table('users').select('id').eq('campaign_id', campaign_id).execute()
    
    if response.data and len(response.data) > 0:
        return jsonify({'message': 'Cannot delete campaign with assigned users'}), 400
        
    # Delete campaign
    response = supabase.table('campaigns').delete().eq('id', campaign_id).execute()
    
    # Log campaign deletion
    log_activity('campaign_deleted', 'campaigns', campaign_id)
    
    return jsonify({'message': 'Campaign deleted successfully'}), 200

