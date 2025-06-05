// Supabase Edge Function for sending emails via SMTP
// This function should be deployed to your Supabase project

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const SMTP_CONFIG = {
  hostname: Deno.env.get("SMTP_HOSTNAME") || "smtp.gmail.com",
  port: parseInt(Deno.env.get("SMTP_PORT") || "587"),
  username: Deno.env.get("SMTP_USERNAME") || "",
  password: Deno.env.get("SMTP_PASSWORD") || "",
}

serve(async (req) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
      }
    })
  }

  try {
    // Verify authorization
    const authHeader = req.headers.get('Authorization')
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return new Response(
        JSON.stringify({ error: 'Missing or invalid authorization header' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Parse request body
    const { to, from, from_name, subject, html, text } = await req.json()

    // Validate required fields
    if (!to || !subject || !html) {
      return new Response(
        JSON.stringify({ error: 'Missing required fields: to, subject, html' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Create email content
    const emailContent = {
      to: [to],
      from: {
        email: from || SMTP_CONFIG.username,
        name: from_name || "Inv_TimeSheetMgmt"
      },
      subject: subject,
      html: html,
      text: text || html.replace(/<[^>]*>/g, '') // Strip HTML tags for text version
    }

    // For this example, we'll use a simple SMTP library
    // In production, you might want to use a service like SendGrid, Mailgun, or AWS SES
    
    // Simulate email sending (replace with actual SMTP implementation)
    console.log('Sending email:', emailContent)
    
    // Here you would implement the actual SMTP sending logic
    // For now, we'll just return success
    
    return new Response(
      JSON.stringify({ 
        success: true, 
        message: 'Email sent successfully',
        to: to,
        subject: subject
      }),
      { 
        status: 200, 
        headers: { 
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        } 
      }
    )

  } catch (error) {
    console.error('Error sending email:', error)
    
    return new Response(
      JSON.stringify({ 
        error: 'Failed to send email', 
        details: error.message 
      }),
      { 
        status: 500, 
        headers: { 
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        } 
      }
    )
  }
})

