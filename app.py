"""
Flask web application for AI Grading System UI
"""
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from project root .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
# Set secret key for session management (OAuth2)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-this-secret-key-in-production-' + str(os.urandom(24)))
CORS(app)

# Import API routes
from api.grading import grading_bp
from api.documents import documents_bp
from api.sections import sections_bp

app.register_blueprint(grading_bp, url_prefix='/api/grading')
app.register_blueprint(documents_bp, url_prefix='/api/documents')
app.register_blueprint(sections_bp, url_prefix='/api')

# Initialize database
from models import init_db
init_db()

@app.route('/')
def index():
    """Serve sections selection page"""
    return render_template('sections.html')

@app.route('/assignments')
def assignments():
    """Serve assignments page for a section"""
    return render_template('assignments.html')

@app.route('/grade')
def grade():
    """Serve grading page for an assignment"""
    return render_template('grade.html')

@app.route('/assignment/<int:assignment_id>')
def assignment_detail(assignment_id):
    """Serve assignment detail page"""
    return render_template('assignment_detail.html')

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

