# Supabase Edge Functions for Inv_TimeSheetMgmt

This directory contains Edge Functions that need to be deployed to your Supabase project to enable certain features of the Inv_TimeSheetMgmt application.

## Functions

### 1. send-email

This function handles sending emails via SMTP. It's used for:
- Welcome emails for new users
- Timesheet submission notifications
- Timesheet approval/rejection notifications
- Password reset emails

## Deployment Instructions

### Prerequisites

1. Install Supabase CLI if you haven't already:
```bash
npm install -g supabase
```

2. Login to Supabase:
```bash
supabase login
```

### Deploying the Functions

1. Navigate to the project root directory:
```bash
cd /path/to/Inv_TimeSheetMgmt
```

2. Link your local project to your Supabase project:
```bash
supabase link --project-ref your-project-id
```

3. Deploy the functions:
```bash
supabase functions deploy send-email
```

### Setting Environment Variables

You need to set the following environment variables for the email function to work:

```bash
supabase secrets set SMTP_HOSTNAME=smtp.yourdomain.com
supabase secrets set SMTP_PORT=587
supabase secrets set SMTP_USERNAME=your-email@yourdomain.com
supabase secrets set SMTP_PASSWORD=your-smtp-password
```

## Testing the Functions

You can test the email function using curl:

```bash
curl -X POST https://your-project-id.supabase.co/functions/v1/send-email \
  -H "Authorization: Bearer YOUR_SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"to":"recipient@example.com","subject":"Test Email","html":"<p>This is a test email</p>"}'
```

## Security Considerations

- The Edge Functions use Supabase's built-in authentication
- Only authenticated requests with valid JWT tokens can access these functions
- For the email function, consider using environment variables for SMTP credentials
- Never expose your SMTP credentials in your code

