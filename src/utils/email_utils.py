import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Supabase SMTP configuration from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@yourdomain.com")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Inv_TimeSheetMgmt")

def send_email(to_email, subject, html_content, text_content=None):
    """
    Send an email using Supabase SMTP
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        html_content (str): HTML content of the email
        text_content (str, optional): Plain text content of the email
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("Supabase configuration missing. Email not sent.")
        return False
        
    # If text_content is not provided, create a simple version from html_content
    if not text_content:
        # Very basic HTML to text conversion
        text_content = html_content.replace('<br>', '\n').replace('</p>', '\n\n').replace('</div>', '\n')
        # Remove all other HTML tags
        import re
        text_content = re.sub('<[^<]+?>', '', text_content)
    
    # Prepare email data
    email_data = {
        "to": to_email,
        "from": SMTP_FROM_EMAIL,
        "from_name": SMTP_FROM_NAME,
        "subject": subject,
        "html": html_content,
        "text": text_content
    }
    
    # Supabase Edge Functions endpoint for sending emails
    # Note: You need to deploy an Edge Function in Supabase for this to work
    email_endpoint = f"{SUPABASE_URL}/functions/v1/send-email"
    
    try:
        # Send request to Supabase Edge Function
        response = requests.post(
            email_endpoint,
            json=email_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"
            }
        )
        
        # Check if email was sent successfully
        if response.status_code == 200:
            return True
        else:
            print(f"Failed to send email. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def send_timesheet_submitted_notification(approver_email, submitter_name, date, timesheet_id):
    """
    Send notification when a timesheet is submitted for approval
    
    Args:
        approver_email (str): Email of the approver
        submitter_name (str): Name of the person who submitted the timesheet
        date (str): Date of the timesheet
        timesheet_id (str): ID of the timesheet
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = f"Timesheet Submitted for Approval - {date}"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Timesheet Submitted for Approval</h2>
        <p>A timesheet has been submitted for your approval:</p>
        <ul>
            <li><strong>Submitted by:</strong> {submitter_name}</li>
            <li><strong>Date:</strong> {date}</li>
        </ul>
        <p>Please review and approve or reject this timesheet at your earliest convenience.</p>
        <p>
            <a href="{os.getenv('FRONTEND_URL', '')}/timesheets/{timesheet_id}" 
               style="background-color: #4CAF50; color: white; padding: 10px 15px; 
                      text-decoration: none; border-radius: 4px; display: inline-block;">
                Review Timesheet
            </a>
        </p>
        <p>Thank you,<br>Inv_TimeSheetMgmt Team</p>
    </div>
    """
    
    return send_email(approver_email, subject, html_content)

def send_timesheet_approved_notification(user_email, approver_name, date, timesheet_id):
    """
    Send notification when a timesheet is approved
    
    Args:
        user_email (str): Email of the user whose timesheet was approved
        approver_name (str): Name of the approver
        date (str): Date of the timesheet
        timesheet_id (str): ID of the timesheet
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = f"Timesheet Approved - {date}"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Timesheet Approved</h2>
        <p>Your timesheet has been approved:</p>
        <ul>
            <li><strong>Date:</strong> {date}</li>
            <li><strong>Approved by:</strong> {approver_name}</li>
        </ul>
        <p>
            <a href="{os.getenv('FRONTEND_URL', '')}/timesheets/{timesheet_id}" 
               style="background-color: #4CAF50; color: white; padding: 10px 15px; 
                      text-decoration: none; border-radius: 4px; display: inline-block;">
                View Timesheet
            </a>
        </p>
        <p>Thank you,<br>Inv_TimeSheetMgmt Team</p>
    </div>
    """
    
    return send_email(user_email, subject, html_content)

def send_timesheet_rejected_notification(user_email, approver_name, date, comments, timesheet_id):
    """
    Send notification when a timesheet is rejected
    
    Args:
        user_email (str): Email of the user whose timesheet was rejected
        approver_name (str): Name of the approver
        date (str): Date of the timesheet
        comments (str): Rejection comments
        timesheet_id (str): ID of the timesheet
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = f"Timesheet Rejected - {date}"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Timesheet Rejected</h2>
        <p>Your timesheet has been rejected:</p>
        <ul>
            <li><strong>Date:</strong> {date}</li>
            <li><strong>Rejected by:</strong> {approver_name}</li>
            <li><strong>Comments:</strong> {comments}</li>
        </ul>
        <p>Please update your timesheet and resubmit it for approval.</p>
        <p>
            <a href="{os.getenv('FRONTEND_URL', '')}/timesheets/{timesheet_id}/edit" 
               style="background-color: #f44336; color: white; padding: 10px 15px; 
                      text-decoration: none; border-radius: 4px; display: inline-block;">
                Edit Timesheet
            </a>
        </p>
        <p>Thank you,<br>Inv_TimeSheetMgmt Team</p>
    </div>
    """
    
    return send_email(user_email, subject, html_content)

def send_reminder_notification(user_email, user_name, missing_dates):
    """
    Send reminder to submit timesheets for missing dates
    
    Args:
        user_email (str): Email of the user to remind
        user_name (str): Name of the user
        missing_dates (list): List of dates with missing timesheets
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = "Reminder: Submit Your Timesheets"
    
    # Format dates for display
    formatted_dates = "<li>" + "</li><li>".join(missing_dates) + "</li>"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Timesheet Submission Reminder</h2>
        <p>Hello {user_name},</p>
        <p>This is a friendly reminder that you have not submitted timesheets for the following dates:</p>
        <ul>
            {formatted_dates}
        </ul>
        <p>Please submit your timesheets as soon as possible.</p>
        <p>
            <a href="{os.getenv('FRONTEND_URL', '')}/timesheets/new" 
               style="background-color: #2196F3; color: white; padding: 10px 15px; 
                      text-decoration: none; border-radius: 4px; display: inline-block;">
                Submit Timesheets
            </a>
        </p>
        <p>Thank you,<br>Inv_TimeSheetMgmt Team</p>
    </div>
    """
    
    return send_email(user_email, subject, html_content)

def send_welcome_email(user_email, user_name, temp_password=None):
    """
    Send welcome email to new users
    
    Args:
        user_email (str): Email of the new user
        user_name (str): Name of the new user
        temp_password (str, optional): Temporary password for the user
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = "Welcome to Inv_TimeSheetMgmt"
    
    password_section = ""
    if temp_password:
        password_section = f"""
        <p>Your temporary password is: <strong>{temp_password}</strong></p>
        <p>Please change your password after your first login.</p>
        """
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Welcome to Inv_TimeSheetMgmt!</h2>
        <p>Hello {user_name},</p>
        <p>Your account has been created in the Inv_TimeSheetMgmt system.</p>
        {password_section}
        <p>
            <a href="{os.getenv('FRONTEND_URL', '')}/login" 
               style="background-color: #2196F3; color: white; padding: 10px 15px; 
                      text-decoration: none; border-radius: 4px; display: inline-block;">
                Login to Your Account
            </a>
        </p>
        <p>If you have any questions, please contact your administrator.</p>
        <p>Thank you,<br>Inv_TimeSheetMgmt Team</p>
    </div>
    """
    
    return send_email(user_email, subject, html_content)

