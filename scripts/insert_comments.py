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


def extract_text_with_indices(doc):
    """
    Extract all text from document with accurate character indices.
    Returns a list of text segments with their start and end indices.
    """
    text_segments = []
    current_index = 1  # Google Docs indices start at 1
    
    def process_element(element):
        nonlocal current_index
        if 'paragraph' in element:
            para = element['paragraph']
            for elem in para.get('elements', []):
                if 'textRun' in elem:
                    text = elem['textRun'].get('content', '')
                    if text:  # Only add non-empty text
                        start = current_index
                        end = current_index + len(text)
                        text_segments.append({
                            'text': text,
                            'start': start,
                            'end': end
                        })
                        current_index = end
                elif 'pageBreak' in elem:
                    # Page breaks don't add to text index
                    pass
        elif 'table' in element:
            # Process table cells
            table = element['table']
            for row in table.get('tableRows', []):
                for cell in row.get('tableCells', []):
                    for content_elem in cell.get('content', []):
                        process_element(content_elem)
        elif 'sectionBreak' in element:
            # Section breaks
            pass
    
    # Process all body content
    body = doc.get('body', {})
    for element in body.get('content', []):
        process_element(element)
    
    return text_segments


def find_text_range(doc_service, doc_id, search_text, context_length=50):
    """
    Find the start and end indices of text in a Google Doc.
    Returns (start_index, end_index) tuple.
    
    Args:
        doc_service: Google Docs API service
        doc_id: Document ID
        search_text: Text to search for (can be partial - will find best match)
        context_length: How many characters around the match to include
    
    Returns:
        tuple: (start_index, end_index) or (None, None) if not found
    """
    try:
        doc = doc_service.documents().get(documentId=doc_id).execute()
        text_segments = extract_text_with_indices(doc)
        
        if not text_segments:
            return (None, None)
        
        # Build full text for searching
        full_text = ''.join(seg['text'] for seg in text_segments)
        
        # Clean search text - remove extra whitespace
        search_clean = ' '.join(search_text.split())
        search_lower = search_clean.lower()
        full_text_lower = full_text.lower()
        
        # Try exact match first
        if search_lower in full_text_lower:
            match_start = full_text_lower.find(search_lower)
            match_end = match_start + len(search_clean)
        else:
            # Try to find a substring match (for partial text)
            # Find the longest substring that matches
            best_match = None
            best_length = 0
            
            for i in range(len(search_lower)):
                for j in range(i + 10, len(search_lower) + 1):  # At least 10 chars
                    substring = search_lower[i:j]
                    if substring in full_text_lower:
                        if len(substring) > best_length:
                            best_length = len(substring)
                            best_match = full_text_lower.find(substring)
            
            if best_match is not None:
                match_start = best_match
                match_end = best_match + best_length
            else:
                # If no match found, return None
                print(f"Warning: Could not find text '{search_text[:50]}...' in document", file=sys.stderr)
                return (None, None)
        
        # Find the actual indices in the document
        char_pos = 0
        start_index = None
        end_index = None
        
        for seg in text_segments:
            seg_start = char_pos
            seg_end = char_pos + len(seg['text'])
            
            # Check if match starts in this segment
            if seg_start <= match_start < seg_end:
                offset = match_start - seg_start
                start_index = seg['start'] + offset
            
            # Check if match ends in this segment
            if seg_start < match_end <= seg_end:
                offset = match_end - seg_start
                end_index = seg['start'] + offset
                break
            
            char_pos = seg_end
        
        # If we found start but not end, use start + search length
        if start_index and not end_index:
            end_index = start_index + len(search_clean)
        
        # Add some context around the match for better highlighting
        if start_index:
            start_index = max(1, start_index - min(context_length, start_index - 1))
        if end_index:
            # Get document end to ensure we don't exceed it
            doc_end = text_segments[-1]['end'] if text_segments else 1
            end_index = min(doc_end, end_index + context_length)
        
        return (start_index, end_index)
    
    except Exception as e:
        print(f"Error finding text range: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return (None, None)


def insert_comment(doc_service, doc_id, comment_text, location_text=None, start_index=None):
    """
    Insert a single comment into Google Docs (legacy function - use insert_comments_batch for multiple).
    
    Args:
        doc_service: Google Docs API service
        doc_id: Document ID
        comment_text: Text of the comment
        location_text: Text to search for to place comment (optional)
        start_index: Direct index to place comment (optional)
    """
    try:
        if start_index is None and location_text:
            start_index, _ = find_text_range(doc_service, doc_id, location_text)
            if start_index is None:
                start_index = 1  # Fallback
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
    Insert multiple comments into a Google Doc with proper text range anchoring.
    
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
        
        # Build requests for all comments
        requests = []
        successful_comments = 0
        
        for comment in comments:
            location_text = comment.get('location', '')
            comment_text = comment.get('text', '')
            suggestion = comment.get('suggestion', '')
            
            # Combine text and suggestion
            full_comment = comment_text
            if suggestion:
                full_comment += f"\n\nSuggestion: {suggestion}"
            
            # Find text range for anchoring the comment
            if location_text:
                start_index, end_index = find_text_range(service, doc_id, location_text)
                
                if start_index is None or end_index is None:
                    # Fallback: use a simple index if text not found
                    print(f"Warning: Could not find location '{location_text[:50]}...' for comment, using document start", file=sys.stderr)
                    start_index = 1
                    end_index = 1
            else:
                # No location specified, use document start
                start_index = 1
                end_index = 1
            
            # Create comment request with proper structure
            # Google Docs API requires a range for comments to be anchored to text
            comment_request = {
                'createComment': {
                    'location': {
                        'index': start_index
                    },
                    'content': full_comment
                }
            }
            
            # If we have a range, we can optionally highlight the text
            # Note: Comments are anchored to a location, highlighting is separate
            if start_index != end_index and start_index > 1:
                # Add a text style update to highlight the commented text
                # This makes it easier to see what the comment refers to
                highlight_request = {
                    'updateTextStyle': {
                        'range': {
                            'startIndex': start_index,
                            'endIndex': end_index
                        },
                        'textStyle': {
                            'backgroundColor': {
                                'color': {
                                    'rgbColor': {
                                        'red': 1.0,
                                        'green': 0.9,
                                        'blue': 0.0
                                    }
                                }
                            }
                        },
                        'fields': 'backgroundColor'
                    }
                }
                requests.append(highlight_request)
            
            requests.append(comment_request)
            successful_comments += 1
        
        # Execute batch update
        if requests:
            try:
                service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
                print(f"Successfully inserted {successful_comments} comments with highlighting", file=sys.stderr)
                return True
            except HttpError as http_err:
                # Try without highlighting if that fails
                print(f"Error with highlighting, trying without: {http_err}", file=sys.stderr)
                # Retry with just comments, no highlighting
                comment_only_requests = [req for req in requests if 'createComment' in req]
                if comment_only_requests:
                    service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': comment_only_requests}
                    ).execute()
                    print(f"Successfully inserted {successful_comments} comments (without highlighting)", file=sys.stderr)
                    return True
                raise
        
        return successful_comments > 0
    
    except HttpError as http_err:
        print(f"HTTP Error inserting comments: {http_err}", file=sys.stderr)
        if hasattr(http_err, 'error_details'):
            print(f"Error details: {http_err.error_details}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error inserting comments: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
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

