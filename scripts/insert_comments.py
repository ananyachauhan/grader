"""
Insert comments into Google Docs at specific locations.
"""
import os
import sys
import json
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def get_credentials():
    """Get Google API credentials."""
    creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
    if creds_path and os.path.exists(creds_path):
        return service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/documents',
                   'https://www.googleapis.com/auth/drive']
        )
    
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY or GOOGLE_CREDENTIALS_PATH must be set")
    
    return api_key


def find_text_location(doc_service, doc_id, search_text):
    """
    Find the location of text in a Google Doc.
    Returns the start index of the text.
    """
    try:
        doc = doc_service.documents().get(documentId=doc_id).execute()
        
        # Get all text content
        full_text = ""
        text_runs = []
        
        def extract_text_runs(element, start_index):
            """Extract text runs with their indices."""
            if 'textRun' in element:
                text = element['textRun'].get('content', '')
                end_index = start_index + len(text)
                text_runs.append({
                    'text': text,
                    'start': start_index,
                    'end': end_index
                })
                return end_index
            elif 'paragraph' in element:
                current_index = start_index
                for elem in element['paragraph'].get('elements', []):
                    current_index = extract_text_runs(elem, current_index)
                return current_index + 1  # Add newline
            else:
                current_index = start_index
                for key, value in element.items():
                    if isinstance(value, list):
                        for item in value:
                            current_index = extract_text_runs(item, current_index)
                    elif isinstance(value, dict):
                        current_index = extract_text_runs(value, current_index)
                return current_index
        
        # Extract all text runs
        for element in doc.get('body', {}).get('content', []):
            extract_text_runs(element, len(full_text))
            full_text += " "  # Approximate
        
        # Find search text in document
        doc_text = ""
        for run in text_runs:
            doc_text += run['text']
        
        # Simple search - find first occurrence
        search_lower = search_text.lower()
        doc_lower = doc_text.lower()
        
        if search_lower in doc_lower:
            index = doc_lower.find(search_lower)
            # Find which text run contains this index
            current_pos = 0
            for run in text_runs:
                if current_pos <= index < current_pos + len(run['text']):
                    return run['start'] + (index - current_pos)
                current_pos += len(run['text'])
        
        # If not found, return end of document
        return len(doc_text)
    
    except Exception as e:
        print(f"Error finding text location: {e}", file=sys.stderr)
        return 1  # Default to start of document


def insert_comment(doc_service, doc_id, comment_text, location_text=None, start_index=None):
    """
    Insert a comment into Google Docs.
    
    Args:
        doc_service: Google Docs API service
        doc_id: Document ID
        comment_text: Text of the comment
        location_text: Text to search for to place comment (optional)
        start_index: Direct index to place comment (optional)
    """
    try:
        if start_index is None and location_text:
            start_index = find_text_location(doc_service, doc_id, location_text)
        elif start_index is None:
            start_index = 1  # Default to start
        
        # Create comment request
        requests = [{
            'createComment': {
                'location': {
                    'index': start_index
                },
                'content': comment_text
            }
        }]
        
        # Execute batch update
        doc_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()
        
        return True
    
    except HttpError as error:
        print(f"Error inserting comment: {error}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return False


def insert_comments_batch(doc_id, comments, credentials=None):
    """
    Insert multiple comments into a Google Doc.
    
    Args:
        doc_id: Google Docs document ID
        comments: List of comment dictionaries with 'text', 'location', 'suggestion'
        credentials: Google API credentials
    
    Returns:
        bool: Success status
    """
    try:
        if isinstance(credentials, str):
            service = build('docs', 'v1', developerKey=credentials)
        else:
            service = build('docs', 'v1', credentials=credentials)
        
        # Get document to find text locations
        doc = service.documents().get(documentId=doc_id).execute()
        
        # Build requests for all comments
        requests = []
        
        for comment in comments:
            location_text = comment.get('location', '')
            comment_text = comment.get('text', '')
            suggestion = comment.get('suggestion', '')
            
            # Combine text and suggestion
            full_comment = comment_text
            if suggestion:
                full_comment += f"\n\nSuggestion: {suggestion}"
            
            # Find location
            start_index = find_text_location(service, doc_id, location_text) if location_text else 1
            
            # Create comment request
            requests.append({
                'createComment': {
                    'location': {
                        'index': start_index
                    },
                    'content': full_comment
                }
            })
        
        # Execute batch update
        if requests:
            service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
        
        return True
    
    except Exception as e:
        print(f"Error inserting comments: {e}", file=sys.stderr)
        return False


def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 3:
        print("Usage: python insert_comments.py <document_id> <comments_json_file>", file=sys.stderr)
        sys.exit(1)
    
    doc_id = sys.argv[1]
    comments_file = sys.argv[2]
    
    try:
        # Load comments
        with open(comments_file, 'r', encoding='utf-8') as f:
            comments_data = json.load(f)
        
        # Handle both list and dict formats
        if isinstance(comments_data, dict) and 'comments' in comments_data:
            comments = comments_data['comments']
        elif isinstance(comments_data, list):
            comments = comments_data
        else:
            comments = [comments_data]
        
        # Get credentials
        credentials = get_credentials()
        
        # Insert comments
        success = insert_comments_batch(doc_id, comments, credentials)
        
        if success:
            print(f"Successfully inserted {len(comments)} comments")
        else:
            print("Failed to insert comments", file=sys.stderr)
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

