# Railway Deployment Guide for Inv_TimeSheetMgmt Backend

## Prerequisites
- Railway account (✅ You have this)
- GitHub account (recommended)
- Supabase project with database

## Deployment Steps

### 1. Push Code to GitHub (Recommended Method)

```bash
# Initialize git repository (if not already done)
git init
git add .
git commit -m "Initial commit - Inv_TimeSheetMgmt backend"

# Add your GitHub repository
git remote add origin https://github.com/yourusername/inv-timesheet-backend.git
git branch -M main
git push -u origin main
```

### 2. Deploy to Railway

#### Option A: GitHub Integration (Recommended)
1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will automatically detect it's a Python app

#### Option B: Railway CLI
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Deploy
railway up
```

### 3. Configure Environment Variables in Railway

Go to your Railway project dashboard and add these environment variables:

```
SUPABASE_URL=your-supabase-project-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
FLASK_SECRET_KEY=your-production-secret-key-here
FLASK_ENV=production
FLASK_DEBUG=0
JWT_SECRET_KEY=your-production-jwt-secret-key-here
JWT_ACCESS_TOKEN_EXPIRES=3600
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=Inv_TimeSheetMgmt
FRONTEND_URL=https://your-domain.com
```

### 4. Generate Secret Keys

Use these commands to generate secure secret keys:

```python
import secrets
print("FLASK_SECRET_KEY:", secrets.token_urlsafe(32))
print("JWT_SECRET_KEY:", secrets.token_urlsafe(32))
```

### 5. Test Deployment

After deployment, your API will be available at:
- `https://your-app-name.railway.app`
- Health check: `https://your-app-name.railway.app/health`
- API info: `https://your-app-name.railway.app/api`

### 6. Custom Domain (Optional)

1. In Railway dashboard, go to Settings
2. Add your custom domain
3. Configure DNS records as instructed

## Files Created for Railway:
- `railway.toml` - Railway configuration
- `Procfile` - Process configuration
- `requirements.txt` - Python dependencies (updated with gunicorn)
- `.env.production` - Environment variables template
- `.gitignore` - Git ignore file

## Next Steps:
1. Set up Supabase database
2. Deploy to Railway
3. Configure environment variables
4. Test API endpoints
5. Deploy frontend to Vercel

## Troubleshooting:
- Check Railway logs in the dashboard
- Ensure all environment variables are set
- Verify Supabase connection
- Check health endpoint: `/health`

