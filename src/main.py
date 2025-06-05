import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routes
from src.routes.auth import auth_bp
from src.routes.users import users_bp
from src.routes.campaigns import campaigns_bp
from src.routes.schedules import schedules_bp
from src.routes.timesheets import timesheets_bp
from src.routes.reports import reports_bp

# Create Flask app
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Enable CORS - Allow frontend domain in production
frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
allowed_origins = [frontend_url, 'http://localhost:3000', 'http://localhost:5173']

CORS(app, resources={
    r"/api/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Set secret key
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-replace-in-production')

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(users_bp, url_prefix='/api/users')
app.register_blueprint(campaigns_bp, url_prefix='/api/campaigns')
app.register_blueprint(schedules_bp, url_prefix='/api/schedules')
app.register_blueprint(timesheets_bp, url_prefix='/api/timesheets')
app.register_blueprint(reports_bp, url_prefix='/api/reports')

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'message': 'Internal server error'}), 500

# Serve static files
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Health check endpoint for Railway
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy', 
        'message': 'Inv_TimeSheetMgmt API is running',
        'environment': os.getenv('FLASK_ENV', 'development')
    })

# API info endpoint
@app.route('/api')
def api_info():
    return jsonify({
        'name': 'Inv_TimeSheetMgmt API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'auth': '/api/auth',
            'users': '/api/users',
            'campaigns': '/api/campaigns',
            'schedules': '/api/schedules',
            'timesheets': '/api/timesheets',
            'reports': '/api/reports'
        }
    })

if __name__ == '__main__':
    # Get port from environment variable (Railway sets this)
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    
    app.run(host='0.0.0.0', port=port, debug=debug)

