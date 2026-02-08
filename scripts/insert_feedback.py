"""
Insert structured feedback text into Google Docs on a new page.
"""
import os
import sys
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


def insert_feedback_text(doc_id, strengths, key_issues, suggestions, credentials=None, page_title="Feedback"):
    """
    Insert structured feedback text into Google Docs on a new page.
    
    Args:
        doc_id: Google Docs document ID
        strengths: Text describing strengths
        key_issues: Text describing key issues
        suggestions: Text with suggestions for improvement
        credentials: Google API credentials
        page_title: Title for the feedback page
    
    Returns:
        bool: Success status
    """
    try:
        if isinstance(credentials, str):
            service = build('docs', 'v1', developerKey=credentials)
        else:
            service = build('docs', 'v1', credentials=credentials)
        
        # Get document end index
        doc = service.documents().get(documentId=doc_id).execute()
        body = doc.get('body', {})
        content = body.get('content', [])
        
        # Calculate end index
        end_index = 1
        for element in content:
            if 'endIndex' in element:
                end_index = max(end_index, element['endIndex'])
        
        # Insert before the end
        insert_index = max(1, end_index - 1)
        
        requests = []
        
        # Insert page break
        requests.append({
            'insertPageBreak': {
                'location': {
                    'index': insert_index
                }
            }
        })
        
        # Update end index after page break
        end_index = insert_index + 1
        
        # Insert title
        requests.append({
            'insertText': {
                'location': {
                    'index': end_index
                },
                'text': f"{page_title}\n\n"
            }
        })
        
        # Style the title
        title_end = end_index + len(page_title) + 2
        requests.append({
            'updateTextStyle': {
                'range': {
                    'startIndex': end_index,
                    'endIndex': title_end - 1
                },
                'textStyle': {
                    'bold': True,
                    'fontSize': {
                        'magnitude': 18,
                        'unit': 'PT'
                    }
                },
                'fields': 'bold,fontSize'
            }
        })
        
        current_index = title_end
        
        # Insert Strengths section
        if strengths and strengths.strip():
            strengths_text = f"Strengths\n{strengths.strip()}\n\n"
            strengths_start = current_index
            requests.append({
                'insertText': {
                    'location': {
                        'index': current_index
                    },
                    'text': strengths_text
                }
            })
            
            # Style section heading
            strengths_heading_end = current_index + len("Strengths")
            requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': strengths_heading_end
                    },
                    'textStyle': {
                        'bold': True,
                        'fontSize': {
                            'magnitude': 14,
                            'unit': 'PT'
                        }
                    },
                    'fields': 'bold,fontSize'
                }
            })
            
            current_index += len(strengths_text)
        
        # Insert Key Issues section
        if key_issues and key_issues.strip():
            issues_text = f"Key Issues\n{key_issues.strip()}\n\n"
            issues_start = current_index
            requests.append({
                'insertText': {
                    'location': {
                        'index': current_index
                    },
                    'text': issues_text
                }
            })
            
            # Style section heading
            issues_heading_end = current_index + len("Key Issues")
            requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': issues_heading_end
                    },
                    'textStyle': {
                        'bold': True,
                        'fontSize': {
                            'magnitude': 14,
                            'unit': 'PT'
                        }
                    },
                    'fields': 'bold,fontSize'
                }
            })
            
            current_index += len(issues_text)
        
        # Insert Suggestions section
        if suggestions and suggestions.strip():
            suggestions_text = f"Suggestions for Improvement\n{suggestions.strip()}\n\n"
            suggestions_start = current_index
            requests.append({
                'insertText': {
                    'location': {
                        'index': current_index
                    },
                    'text': suggestions_text
                }
            })
            
            # Style section heading
            suggestions_heading_end = current_index + len("Suggestions for Improvement")
            requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': suggestions_heading_end
                    },
                    'textStyle': {
                        'bold': True,
                        'fontSize': {
                            'magnitude': 14,
                            'unit': 'PT'
                        }
                    },
                    'fields': 'bold,fontSize'
                }
            })
            
            current_index += len(suggestions_text)
        
        # Execute all requests
        if requests:
            service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
        
        return True
    
    except HttpError as error:
        print(f"Error inserting feedback: {error}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import json
    
    if len(sys.argv) < 5:
        print("Usage: python insert_feedback.py <document_id> <strengths> <key_issues> <suggestions>", file=sys.stderr)
        sys.exit(1)
    
    doc_id = sys.argv[1]
    strengths = sys.argv[2]
    key_issues = sys.argv[3]
    suggestions = sys.argv[4]
    
    try:
        credentials = get_credentials()
        success = insert_feedback_text(doc_id, strengths, key_issues, suggestions, credentials)
        
        if success:
            print("Successfully inserted feedback")
        else:
            print("Failed to insert feedback", file=sys.stderr)
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

