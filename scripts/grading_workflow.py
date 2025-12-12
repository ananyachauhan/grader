"""
Main grading workflow orchestrator.
Coordinates all operations: extract text, AI grading, insert comments, insert rubric.
"""
import os
import sys
import json
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from extract_text import extract_text_from_doc, get_credentials as get_docs_credentials
from ai_grader import grade_with_ai, load_rubric
from insert_comments import insert_comments_batch, get_credentials as get_comments_credentials
from insert_rubric import insert_rubric_table, get_credentials as get_rubric_credentials


# Load environment variables
load_dotenv()


def load_config():
    """Load configuration from config.json."""
    config_path = Path(__file__).parent.parent / 'config' / 'config.json'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def grade_document(doc_id, rubric_path=None, config=None):
    """
    Complete grading workflow for a single document.
    
    Args:
        doc_id: Google Docs document ID
        rubric_path: Path to rubric JSON file (optional, uses default from config)
        config: Configuration dictionary (optional)
    
    Returns:
        dict: Result with status, scores, and any errors
    """
    if config is None:
        config = load_config()
    
    # Determine rubric to use
    if rubric_path is None:
        default_rubric = config.get('default_rubric', 'memo_rubric.json')
        rubric_path = Path(__file__).parent.parent / 'rubrics' / default_rubric
    
    if not os.path.exists(rubric_path):
        return {
            'success': False,
            'error': f'Rubric file not found: {rubric_path}',
            'doc_id': doc_id
        }
    
    try:
        # Step 1: Extract text from document
        print(f"Extracting text from document {doc_id}...", file=sys.stderr)
        credentials = get_docs_credentials()
        document_text = extract_text_from_doc(doc_id, credentials)
        
        if not document_text or len(document_text.strip()) < 10:
            return {
                'success': False,
                'error': 'Document appears to be empty or could not extract text',
                'doc_id': doc_id
            }
        
        # Step 2: Load rubric
        print(f"Loading rubric from {rubric_path}...", file=sys.stderr)
        rubric = load_rubric(str(rubric_path))
        
        # Step 3: Grade with AI
        print("Grading with AI...", file=sys.stderr)
        model_name = config.get('ai_model', {}).get('name', 'gemini-pro')
        grading_result = grade_with_ai(document_text, rubric, model_name)
        
        # Step 4: Insert comments
        print(f"Inserting {len(grading_result.get('comments', []))} comments...", file=sys.stderr)
        comments_creds = get_comments_credentials()
        comments_success = insert_comments_batch(
            doc_id,
            grading_result.get('comments', []),
            comments_creds
        )
        
        if not comments_success:
            print("Warning: Some comments may not have been inserted", file=sys.stderr)
        
        # Step 5: Insert rubric table
        print("Inserting rubric table...", file=sys.stderr)
        rubric_creds = get_rubric_credentials()
        page_title = config.get('document', {}).get('rubric_page_title', 'Grading Rubric')
        rubric_success = insert_rubric_table(
            doc_id,
            rubric,
            grading_result.get('scores', {}),
            grading_result.get('total_score', 0),
            rubric_creds,
            page_title
        )
        
        if not rubric_success:
            print("Warning: Rubric table may not have been inserted correctly", file=sys.stderr)
        
        # Return success result
        return {
            'success': True,
            'doc_id': doc_id,
            'scores': grading_result.get('scores', {}),
            'total_score': grading_result.get('total_score', 0),
            'comments_count': len(grading_result.get('comments', [])),
            'summary': grading_result.get('summary', ''),
            'comments_inserted': comments_success,
            'rubric_inserted': rubric_success
        }
    
    except Exception as e:
        print(f"Error in grading workflow: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'doc_id': doc_id
        }


def main():
    """
    Main function for command-line and n8n usage.
    Expects JSON input with document_id and optional rubric_path.
    """
    # Read input from stdin (for n8n) or command line
    if len(sys.argv) > 1:
        # Command line mode
        doc_id = sys.argv[1]
        rubric_path = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        # Read from stdin (n8n mode)
        try:
            input_data = json.loads(sys.stdin.read())
            doc_id = input_data.get('document_id') or input_data.get('doc_id')
            rubric_path = input_data.get('rubric_path')
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error reading input: {e}", file=sys.stderr)
            print("Expected JSON with 'document_id' field, or command line: python grading_workflow.py <doc_id> [rubric_path]", file=sys.stderr)
            sys.exit(1)
    
    if not doc_id:
        print("Error: document_id is required", file=sys.stderr)
        sys.exit(1)
    
    # Run grading workflow
    result = grade_document(doc_id, rubric_path)
    
    # Output result as JSON
    print(json.dumps(result, indent=2))
    
    # Exit with error code if failed
    if not result.get('success'):
        sys.exit(1)


if __name__ == "__main__":
    main()

