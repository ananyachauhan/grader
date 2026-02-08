"""
Extract text content from Google Docs using Google Docs API.
"""
import os
import sys
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json


def get_credentials():
    """Get Google API credentials from OAuth2 token, service account, or API key."""
    from pathlib import Path
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    
    project_root = Path(__file__).parent.parent
    
    # Priority 1: OAuth2 credentials (for accessing user's own Drive)
    token_file = project_root / 'token.json'
    if token_file.exists():
        try:
            # Load token without specifying scopes to avoid scope mismatch errors
            # The token already contains the scopes it was created with
            creds = Credentials.from_authorized_user_file(str(token_file))
            if creds and creds.valid:
                return creds
            # If expired, try to refresh
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed token
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
                return creds
        except Exception as e:
            print(f"Error loading OAuth token: {e}", file=sys.stderr)
    
    # Priority 2: Service account
    creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
    if creds_path and os.path.exists(creds_path):
        return service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/documents',
                   'https://www.googleapis.com/auth/drive']
        )
    
    # Priority 3: API key (limited access)
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("No authentication method available. Please set up OAuth2, service account, or API key.")
    
    return api_key


def extract_text_from_doc(doc_id, credentials=None):
    """
    Extract plain text from a Google Doc.
    
    Args:
        doc_id: Google Docs document ID
        credentials: Google API credentials or API key
    
    Returns:
        str: Plain text content of the document
    """
    try:
        if isinstance(credentials, str):
            # Using API key (limited access)
            service = build('docs', 'v1', developerKey=credentials)
        else:
            # Using OAuth credentials
            service = build('docs', 'v1', credentials=credentials)
        
        # Get document content
        doc = service.documents().get(documentId=doc_id).execute()
        
        # Extract text from all elements
        text_content = []
        
        def extract_text_from_element(element):
            """Recursively extract text from document elements."""
            if 'textRun' in element:
                return element['textRun'].get('content', '')
            elif 'paragraph' in element:
                para_text = ''
                for elem in element['paragraph'].get('elements', []):
                    para_text += extract_text_from_element(elem)
                return para_text + '\n'
            elif 'table' in element:
                table_text = ''
                for row in element['table'].get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        for elem in cell.get('content', []):
                            table_text += extract_text_from_element(elem)
                        table_text += ' | '
                    table_text += '\n'
                return table_text
            else:
                # Recursively process nested elements
                text = ''
                for key, value in element.items():
                    if isinstance(value, list):
                        for item in value:
                            text += extract_text_from_element(item)
                    elif isinstance(value, dict):
                        text += extract_text_from_element(value)
                return text
        
        # Process all content
        for element in doc.get('body', {}).get('content', []):
            text_content.append(extract_text_from_element(element))
        
        return ''.join(text_content).strip()
    
    except HttpError as error:
        print(f"An error occurred: {error}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        raise


def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: python extract_text.py <document_id>", file=sys.stderr)
        sys.exit(1)
    
    doc_id = sys.argv[1]
    
    try:
        credentials = get_credentials()
        text = extract_text_from_doc(doc_id, credentials)
        print(text)
        return text
    except Exception as e:
        print(f"Error extracting text: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

