"""
Insert rubric table into Google Docs on a new page.
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


def get_document_end_index(doc_service, doc_id):
    """Get the index of the end of the document."""
    try:
        doc = doc_service.documents().get(documentId=doc_id).execute()
        body = doc.get('body', {})
        content = body.get('content', [])
        
        if not content:
            return 1
        
        # Find the last element
        last_element = content[-1]
        
        # Calculate end index
        end_index = 1
        for element in content:
            if 'paragraph' in element:
                para = element['paragraph']
                for elem in para.get('elements', []):
                    if 'textRun' in elem:
                        end_index += len(elem['textRun'].get('content', ''))
                end_index += 1  # Newline
            elif 'table' in element:
                # Approximate table size
                end_index += 100
        
        return end_index
    
    except Exception as e:
        print(f"Error getting document end: {e}", file=sys.stderr)
        return 1


def insert_rubric_table(doc_id, rubric, scores, total_score, credentials=None, page_title="Grading Rubric"):
    """
    Insert a rubric table into Google Docs on a new page.
    
    Args:
        doc_id: Google Docs document ID
        rubric: Rubric dictionary with criteria
        scores: Dictionary of scores for each criterion
        total_score: Total score
        credentials: Google API credentials
        page_title: Title for the rubric page
    
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
        
        requests = []
        
        # Insert page break
        requests.append({
            'insertPageBreak': {
                'location': {
                    'index': end_index
                }
            }
        })
        
        # Update end index after page break
        end_index += 1
        
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
                        'magnitude': 16,
                        'unit': 'PT'
                    }
                },
                'fields': 'bold,fontSize'
            }
        })
        
        end_index = title_end
        
        # Create table
        # Table structure: Criterion | Max Points | Points Received
        num_rows = len(rubric['criteria']) + 2  # Header + criteria + total row
        
        # Insert table
        table_start_index = end_index
        requests.append({
            'insertTable': {
                'location': {
                    'index': table_start_index
                },
                'rows': num_rows,
                'columns': 3
            }
        })
        
        # After table insertion, we need to populate it
        # Calculate cell indices (approximate - Google Docs handles this)
        # We'll use a different approach: insert table with content
        
        # Alternative: Insert table rows one by one with content
        # This is simpler but requires knowing cell structure
        
        # For now, let's insert a formatted text table instead
        # Insert table header
        table_text = "\n\nCriterion | Max Points | Points Received\n"
        table_text += "--- | --- | ---\n"
        
        # Insert criteria rows
        for criterion in rubric['criteria']:
            criterion_name = criterion['name']
            max_points = criterion['max_points']
            points_received = scores.get(criterion_name, 0)
            table_text += f"{criterion_name} | {max_points} | {points_received}\n"
        
        # Insert total row
        table_text += f"\n**Total** | **{rubric['total_points']}** | **{total_score}**\n"
        
        # Insert the table text
        requests.append({
            'insertText': {
                'location': {
                    'index': end_index
                },
                'text': table_text
            }
        })
        
        # Execute all requests
        service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()
        
        return True
    
    except HttpError as error:
        print(f"Error inserting rubric: {error}", file=sys.stderr)
        # Fallback: try simpler text-based approach
        return insert_rubric_text_fallback(doc_id, rubric, scores, total_score, credentials, page_title)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return insert_rubric_text_fallback(doc_id, rubric, scores, total_score, credentials, page_title)


def insert_rubric_text_fallback(doc_id, rubric, scores, total_score, credentials, page_title):
    """Fallback method: insert rubric as formatted text."""
    try:
        if isinstance(credentials, str):
            service = build('docs', 'v1', developerKey=credentials)
        else:
            service = build('docs', 'v1', credentials=credentials)
        
        # Get document end
        doc = service.documents().get(documentId=doc_id).execute()
        body = doc.get('body', {})
        content = body.get('content', [])
        
        end_index = 1
        for element in content:
            if 'endIndex' in element:
                end_index = max(end_index, element['endIndex'])
        
        # Build rubric text
        rubric_text = f"\n\n{page_title}\n\n"
        rubric_text += "=" * len(page_title) + "\n\n"
        
        # Add criteria
        for criterion in rubric['criteria']:
            criterion_name = criterion['name']
            max_points = criterion['max_points']
            points_received = scores.get(criterion_name, 0)
            rubric_text += f"{criterion_name}:\n"
            rubric_text += f"  Max Points: {max_points}\n"
            rubric_text += f"  Points Received: {points_received}\n\n"
        
        rubric_text += f"\nTotal Points: {total_score} / {rubric['total_points']}\n"
        
        requests = [
            {
                'insertPageBreak': {
                    'location': {'index': end_index}
                }
            },
            {
                'insertText': {
                    'location': {'index': end_index + 1},
                    'text': rubric_text
                }
            }
        ]
        
        service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()
        
        return True
    
    except Exception as e:
        print(f"Error in fallback method: {e}", file=sys.stderr)
        return False


def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 4:
        print("Usage: python insert_rubric.py <document_id> <rubric_json_file> <scores_json_file>", file=sys.stderr)
        sys.exit(1)
    
    doc_id = sys.argv[1]
    rubric_file = sys.argv[2]
    scores_file = sys.argv[3]
    
    try:
        # Load rubric
        with open(rubric_file, 'r', encoding='utf-8') as f:
            rubric = json.load(f)
        
        # Load scores
        with open(scores_file, 'r', encoding='utf-8') as f:
            scores_data = json.load(f)
        
        if isinstance(scores_data, dict):
            if 'scores' in scores_data:
                scores = scores_data['scores']
                total_score = scores_data.get('total_score', 0)
            else:
                scores = scores_data
                total_score = sum(scores.values())
        else:
            raise ValueError("Scores must be a dictionary")
        
        # Get credentials
        credentials = get_credentials()
        
        # Insert rubric
        success = insert_rubric_table(doc_id, rubric, scores, total_score, credentials)
        
        if success:
            print("Successfully inserted rubric table")
        else:
            print("Failed to insert rubric table", file=sys.stderr)
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

