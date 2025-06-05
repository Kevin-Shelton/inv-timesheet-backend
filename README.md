# Inv_TimeSheetMgmt Backend API

A comprehensive timesheet management system backend built with Flask, designed for BPO operations with role-based access control and Supabase integration.

## 🚀 Features

- **Authentication & Security**
  - JWT-based authentication
  - Role-based access control (Admin, Campaign Lead, Team Member)
  - Password hashing with bcrypt
  - Comprehensive audit logging

- **User Management**
  - Multi-role user system
  - Campaign assignment
  - Pay rate management
  - User profile management

- **Timesheet Management**
  - Clock in/out functionality
  - Break and lunch tracking
  - Approval workflow
  - Overtime calculation

- **Campaign Management**
  - Multiple campaign support
  - Billing rate configuration
  - Team assignment

- **Reporting & Analytics**
  - Campaign summaries
  - Organization-wide reports
  - Time tracking analytics
  - Export capabilities

- **Email Notifications**
  - Supabase SMTP integration
  - Automated notifications for approvals
  - User registration emails

## 🛠️ Tech Stack

- **Backend**: Flask (Python)
- **Database**: Supabase (PostgreSQL)
- **Authentication**: JWT
- **Email**: Supabase SMTP
- **Deployment**: Railway
- **Frontend**: React (separate repository)

## 📋 Prerequisites

- Python 3.11+
- Supabase account and project
- Railway account (for deployment)

## 🔧 Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/inv-timesheet-backend.git
   cd inv-timesheet-backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

5. **Run the application**
   ```bash
   python src/main.py
   ```

The API will be available at `http://localhost:5000`

## 🌐 API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `POST /api/auth/register` - User registration

### Users
- `GET /api/users` - List users (Admin only)
- `GET /api/users/{id}` - Get user details
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user (Admin only)

### Campaigns
- `GET /api/campaigns` - List campaigns
- `POST /api/campaigns` - Create campaign (Admin only)
- `PUT /api/campaigns/{id}` - Update campaign
- `DELETE /api/campaigns/{id}` - Delete campaign (Admin only)

### Timesheets
- `GET /api/timesheets` - List timesheets
- `POST /api/timesheets` - Create timesheet entry
- `PUT /api/timesheets/{id}` - Update timesheet
- `POST /api/timesheets/{id}/submit` - Submit for approval
- `POST /api/timesheets/{id}/approve` - Approve timesheet
- `POST /api/timesheets/{id}/reject` - Reject timesheet

### Reports
- `GET /api/reports/campaign/{id}` - Campaign summary
- `GET /api/reports/organization` - Organization summary
- `GET /api/reports/export` - Export data

## 🚀 Deployment to Railway

1. **Push to GitHub** (this repository)

2. **Connect to Railway**
   - Go to [railway.app](https://railway.app)
   - Create new project
   - Connect GitHub repository
   - Railway will auto-deploy

3. **Set Environment Variables in Railway**
   ```
   SUPABASE_URL=your-supabase-url
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   FLASK_SECRET_KEY=your-secret-key
   JWT_SECRET_KEY=your-jwt-secret
   FLASK_ENV=production
   FRONTEND_URL=https://your-frontend-domain.com
   ```

4. **Deploy**
   - Railway will automatically build and deploy
   - Your API will be available at `https://your-app.railway.app`

## 📊 Database Schema

The application uses Supabase with the following main tables:
- `users` - User accounts and profiles
- `campaigns` - Campaign/project management
- `schedules` - Work schedules
- `timesheet_entries` - Time tracking entries
- `audit_logs` - System audit trail

See `/database/` folder for complete SQL schema.

## 🔐 Security Features

- JWT token authentication
- Role-based access control
- Password hashing with bcrypt
- CORS protection
- Input validation
- Audit logging
- Row Level Security (RLS) in Supabase

## 📧 Email Integration

Uses Supabase SMTP for:
- User registration confirmations
- Timesheet approval notifications
- Password reset emails
- System notifications

## 🧪 Testing

```bash
# Run tests (when implemented)
python -m pytest

# Health check
curl https://your-app.railway.app/health
```

## 📝 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | Yes |
| `FLASK_SECRET_KEY` | Flask secret key | Yes |
| `JWT_SECRET_KEY` | JWT signing key | Yes |
| `FLASK_ENV` | Environment (development/production) | No |
| `FRONTEND_URL` | Frontend application URL | Yes |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Create an issue in this repository
- Check the deployment guide: `RAILWAY_DEPLOYMENT.md`
- Review the API documentation

## 🔗 Related Repositories

- Frontend (React): [Link to frontend repository]
- Database Schema: See `/database/` folder in this repository

