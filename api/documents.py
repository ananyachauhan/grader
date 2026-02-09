"""
Document listing API endpoints
"""
from flask import Blueprint, jsonify, request, session, url_for
import os
from pathlib import Path
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import json
import base64
import tempfile

# Allow HTTP for localhost development (OAuth2)
# This is safe for localhost only - in production, set OAUTHLIB_INSECURE_TRANSPORT=0
if 'OAUTHLIB_INSECURE_TRANSPORT' not in os.environ:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Default to 1 for local dev

# Load environment variables from project root .env file
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

documents_bp = Blueprint('documents', __name__)

# OAuth2 scopes needed
SCOPES = [
    'https://www.googleapis.com/auth/drive',  # Full Drive access (needed for copying files)
    'https://www.googleapis.com/auth/documents'  # Full Docs access (includes read and write)
]

def get_client_secrets_path():
    """Get client secrets file path, checking for base64 env var first"""
    # Check for base64 encoded secrets in environment variable first (for Fly.io)
    client_secrets_b64 = os.getenv('GOOGLE_CLIENT_SECRETS_B64')
    if client_secrets_b64:
        # Decode and create temporary file
        try:
            client_secrets_data = base64.b64decode(client_secrets_b64).decode('utf-8')
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            temp_file.write(client_secrets_data)
            temp_file.close()
            return temp_file.name
        except Exception as e:
            print(f"Error decoding client secrets from environment: {e}", flush=True)
            # Fall through to file path
    
    # Fallback to file path (for local development)
    client_secrets_file = os.getenv('GOOGLE_CLIENT_SECRETS_FILE', 'client_secrets.json')
    client_secrets_path = project_root / client_secrets_file
    
    if not client_secrets_path.exists():
        return None
    
    return str(client_secrets_path)

def get_oauth_credentials():
    """Get OAuth2 credentials from token file (supports Fly.io persistent storage)"""
    # Check for Fly.io persistent volume path
    fly_volume_path = os.getenv('FLY_VOLUME_PATH', '/data')
    token_file = Path(fly_volume_path) / 'token.json'
    
    # Fallback to local path for development
    if not token_file.parent.exists():
        token_file = project_root / 'token.json'
    
    # Check if we have stored credentials
    if token_file.exists():
        try:
            # Load token without specifying scopes to avoid scope mismatch errors
            # The token already contains the scopes it was created with
            # Google may grant additional scopes (like .readonly versions) which is fine
            creds = Credentials.from_authorized_user_file(str(token_file))
            if creds and creds.valid:
                return creds
            # If expired, try to refresh
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed token
                token_file.parent.mkdir(parents=True, exist_ok=True)
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
                return creds
        except Exception as e:
            print(f"Error loading OAuth token: {e}", flush=True)
    
    return None

def get_drive_service():
    """Get Google Drive service with OAuth2, service account, or API key (in priority order)"""
    # Priority 1: OAuth2 credentials (for accessing user's own Drive)
    oauth_creds = get_oauth_credentials()
    if oauth_creds:
        return build('drive', 'v3', credentials=oauth_creds)
    
    # Priority 2: Service account
    creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
    if creds_path and os.path.exists(creds_path):
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive']  # Full drive access
        )
        return build('drive', 'v3', credentials=creds)
    
    # Priority 3: API key (limited access - may not work for private folders)
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("No authentication method available. Please set up OAuth2, service account, or API key.")
    return build('drive', 'v3', developerKey=api_key)

@documents_bp.route('/auth/status', methods=['GET'])
def auth_status():
    """Check OAuth2 authentication status"""
    creds = get_oauth_credentials()
    if creds:
        return jsonify({
            'authenticated': True,
            'message': 'Authenticated with Google account'
        })
    else:
        return jsonify({
            'authenticated': False,
            'message': 'Not authenticated. Please authenticate to access Drive files.'
        })

@documents_bp.route('/auth', methods=['GET'])
def auth():
    """Initiate OAuth2 flow"""
    client_secrets_path = get_client_secrets_path()
    
    if not client_secrets_path:
        return jsonify({
            'error': 'OAuth2 client secrets file not found',
            'instructions': 'Download OAuth2 credentials from Google Cloud Console and save as client_secrets.json in the project root, or set GOOGLE_CLIENT_SECRETS_B64 environment variable'
        }), 400
    
    try:
        # Manually construct HTTPS URL for production (Fly.io)
        # Check if we're on Fly.io or behind a proxy that uses HTTPS
        if os.getenv('FLY_APP_NAME') or request.headers.get('X-Forwarded-Proto') == 'https':
            # Production - use HTTPS
            redirect_uri = "https://grader-ai.fly.dev/api/documents/auth/callback"
        else:
            # Local development - use url_for
            redirect_uri = url_for('documents.oauth_callback', _external=True)
        
        flow = Flow.from_client_secrets_file(
            client_secrets_path,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='false',  # Don't include previously granted scopes to avoid scope conflicts
            prompt='consent'  # Force consent to get refresh token
        )
        
        # Store state in session
        session['oauth_state'] = state
        
        return jsonify({
            'auth_url': authorization_url,
            'message': 'Please visit the auth_url to authenticate with your Google account'
        })
    except Exception as e:
        return jsonify({
            'error': f'Error initiating OAuth flow: {str(e)}'
        }), 500

@documents_bp.route('/auth/callback', methods=['GET'])
def oauth_callback():
    """OAuth2 callback handler"""
    if 'error' in request.args:
        return f"""
        <html>
        <head><title>Authentication Error</title></head>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h2>Authentication Error</h2>
            <p>{request.args.get('error')}</p>
            <p><a href="/grade">Return to Grading Page</a></p>
        </body>
        </html>
        """, 400
    
    if 'oauth_state' not in session:
        return """
        <html>
        <head><title>Authentication Error</title></head>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h2>Invalid Session</h2>
            <p>Please try authenticating again.</p>
            <p><a href="/grade">Return to Grading Page</a></p>
        </body>
        </html>
        """, 400
    
    try:
        client_secrets_path = get_client_secrets_path()
        
        if not client_secrets_path:
            return """
            <html>
            <head><title>Authentication Error</title></head>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h2>Configuration Error</h2>
                <p>OAuth2 client secrets not configured. Please set GOOGLE_CLIENT_SECRETS_B64 or provide client_secrets.json file.</p>
                <p><a href="/grade">Return to Grading Page</a></p>
            </body>
            </html>
            """, 500
        
        # Manually construct HTTPS URL for production (Fly.io)
        # Check if we're on Fly.io or behind a proxy that uses HTTPS
        if os.getenv('FLY_APP_NAME') or request.headers.get('X-Forwarded-Proto') == 'https':
            # Production - use HTTPS
            redirect_uri = "https://grader-ai.fly.dev/api/documents/auth/callback"
        else:
            # Local development - use url_for
            redirect_uri = url_for('documents.oauth_callback', _external=True)
        
        flow = Flow.from_client_secrets_file(
            client_secrets_path,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
            state=session['oauth_state']
        )
        
        flow.fetch_token(authorization_response=request.url)
        
        # Save credentials (use persistent storage on Fly.io)
        creds = flow.credentials
        fly_volume_path = os.getenv('FLY_VOLUME_PATH', '/data')
        token_file = Path(fly_volume_path) / 'token.json'
        
        # Fallback to local path for development
        if not token_file.parent.exists():
            token_file = project_root / 'token.json'
        
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        
        session.pop('oauth_state', None)
        
        return """
        <html>
        <head><title>Authentication Successful</title></head>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h2 style="color: #2d7a32;">✓ Authentication Successful!</h2>
            <p>You can now access your Google Drive files.</p>
            <p><a href="/grade" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background: #500000; color: white; text-decoration: none; border-radius: 4px;">Return to Grading Page</a></p>
            <script>
                setTimeout(function() {
                    window.close();
                }, 2000);
            </script>
        </body>
        </html>
        """
    except Exception as e:
        return f"""
        <html>
        <head><title>Authentication Error</title></head>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h2>Authentication Error</h2>
            <p>Error: {str(e)}</p>
            <p><a href="/grade">Return to Grading Page</a></p>
        </body>
        </html>
        """, 500

@documents_bp.route('/list', methods=['GET'])
def list_documents():
    """List Google Docs and Word documents in a folder"""
    folder_id = request.args.get('folder_id') or os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    
    if not folder_id:
        return jsonify({'error': 'folder_id is required'}), 400
    
    try:
        service = get_drive_service()
        
        # Query for both Google Docs and Word documents
        query = f"'{folder_id}' in parents and (mimeType='application/vnd.google-apps.document' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document' or mimeType='application/msword') and trashed=false"
        
        results = service.files().list(
            q=query,
            fields="files(id, name, modifiedTime, webViewLink, mimeType)",
            orderBy="modifiedTime desc"
        ).execute()
        
        documents = []
        for file in results.get('files', []):
            mime_type = file.get('mimeType', '')
            is_word_doc = mime_type in [
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
                'application/msword'  # .doc
            ]
            
            # For Word docs, the webViewLink might not exist, so create a Drive link
            url = file.get('webViewLink')
            if not url and is_word_doc:
                url = f"https://drive.google.com/file/d/{file['id']}/view"
            elif not url:
                url = f"https://docs.google.com/document/d/{file['id']}"
            
            documents.append({
                'id': file['id'],
                'name': file['name'],
                'modified_time': file.get('modifiedTime', ''),
                'url': url,
                'mime_type': mime_type,
                'is_word_doc': is_word_doc,
                'file_type': 'Word Document' if is_word_doc else 'Google Doc'
            })
        
        return jsonify({
            'documents': documents,
            'count': len(documents)
        })
    
    except HttpError as e:
        # Handle Google API specific errors
        if e.resp.status == 401:
            # Unauthorized - need to re-authenticate
            return jsonify({
                'error': 'Authentication required',
                'auth_required': True,
                'auth_url': url_for('documents.auth', _external=True)
            }), 401
        error_details = f"Google API Error: {e.resp.status} - {e.error_details if hasattr(e, 'error_details') else str(e)}"
        return jsonify({'error': error_details}), 500
    except ValueError as e:
        # Handle missing API key or credentials
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        # Log the full error for debugging
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error listing documents: {error_trace}", flush=True)
        return jsonify({'error': f'Error listing documents: {str(e)}'}), 500

