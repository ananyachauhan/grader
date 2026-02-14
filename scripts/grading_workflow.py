"""
Main grading workflow orchestrator.
Coordinates all operations: extract text, AI grading, insert feedback, insert rubric.
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
from insert_feedback import insert_feedback_text, get_credentials as get_feedback_credentials
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


def convert_word_to_google_doc(word_file_id, credentials=None):
    """
    Convert a Word document to Google Docs format.
    
    Args:
        word_file_id: Google Drive file ID of the Word document
        credentials: Google API credentials
    
    Returns:
        str: Google Docs document ID of the converted document
    
    Raises:
        Exception: If conversion fails
    """
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    
    try:
        if isinstance(credentials, str):
            drive_service = build('drive', 'v3', developerKey=credentials)
        else:
            drive_service = build('drive', 'v3', credentials=credentials)
        
        # Get the original file name
        try:
            file_metadata = drive_service.files().get(fileId=word_file_id, fields='name').execute()
            original_name = file_metadata.get('name', 'Converted Document')
        except HttpError as e:
            raise Exception(f"Could not access Word document {word_file_id}: {str(e)}")
        
        # Remove .docx or .doc extension if present
        base_name = original_name
        if base_name.endswith('.docx'):
            base_name = base_name[:-5]
        elif base_name.endswith('.doc'):
            base_name = base_name[:-4]
        
        # Create a copy with conversion to Google Docs format
        try:
            converted_file = drive_service.files().copy(
                fileId=word_file_id,
                body={
                    'name': f"{base_name} (Graded)",
                    'mimeType': 'application/vnd.google-apps.document'
                }
            ).execute()
            
            converted_id = converted_file.get('id')
            if not converted_id:
                raise Exception("Conversion succeeded but no document ID was returned")
            
            return converted_id
        except HttpError as e:
            raise Exception(f"Failed to convert Word document to Google Docs: {str(e)}")
    except Exception as e:
        # Re-raise with more context
        if "HttpError" not in str(type(e)):
            raise Exception(f"Error during Word document conversion: {str(e)}")
        raise


def rename_document_to_graded(doc_id, credentials=None):
    """
    Rename a Google Docs file to include "Graded" in the name.
    
    Args:
        doc_id: Google Drive file ID of the document
        credentials: Google API credentials
    
    Returns:
        bool: True if rename was successful, False otherwise
    """
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    
    try:
        if isinstance(credentials, str):
            drive_service = build('drive', 'v3', developerKey=credentials)
        else:
            drive_service = build('drive', 'v3', credentials=credentials)
        
        # Get the current file name
        try:
            file_metadata = drive_service.files().get(fileId=doc_id, fields='name').execute()
            current_name = file_metadata.get('name', 'Document')
        except HttpError as e:
            print(f"Warning: Could not get document name for {doc_id}: {str(e)}", file=sys.stderr)
            return False
        
        # Check if already has "Graded" in the name
        if ' (Graded)' in current_name or ' - Graded' in current_name:
            print(f"Document {doc_id} already has 'Graded' in name, skipping rename", file=sys.stderr)
            return True
        
        # Add " (Graded)" to the name
        new_name = f"{current_name} (Graded)"
        
        # Update the file name
        try:
            drive_service.files().update(
                fileId=doc_id,
                body={'name': new_name},
                fields='name'
            ).execute()
            print(f"Successfully renamed document {doc_id} to '{new_name}'", file=sys.stderr)
            return True
        except HttpError as e:
            error_msg = f"Failed to rename document {doc_id}: {str(e)}"
            print(f"Warning: {error_msg}", file=sys.stderr)
            return False
    
    except Exception as e:
        error_msg = f"Error renaming document {doc_id}: {str(e)}"
        print(f"Warning: {error_msg}", file=sys.stderr)
        return False


def delete_word_document(word_file_id, credentials=None):
    """
    Delete a Word document from Google Drive.
    
    Args:
        word_file_id: Google Drive file ID of the Word document to delete
        credentials: Google API credentials
    
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    
    try:
        if isinstance(credentials, str):
            drive_service = build('drive', 'v3', developerKey=credentials)
        else:
            drive_service = build('drive', 'v3', credentials=credentials)
        
        # Delete the file
        drive_service.files().delete(fileId=word_file_id).execute()
        print(f"Successfully deleted original Word document {word_file_id}", file=sys.stderr)
        return True
    
    except HttpError as e:
        error_msg = f"Failed to delete Word document {word_file_id}: {str(e)}"
        print(f"Warning: {error_msg}", file=sys.stderr)
        # Don't raise - deletion failure shouldn't break the workflow
        return False
    except Exception as e:
        error_msg = f"Error deleting Word document {word_file_id}: {str(e)}"
        print(f"Warning: {error_msg}", file=sys.stderr)
        return False


def grade_document(doc_id, rubric_path=None, config=None, custom_instructions=None, is_word_doc=False):
    """
    Complete grading workflow for a single document.
    
    Args:
        doc_id: Google Docs document ID (or Word doc ID if is_word_doc=True)
        rubric_path: Path to rubric JSON file (optional, uses default from config)
        config: Configuration dictionary (optional)
        custom_instructions: Optional custom instructions for the AI grader
        is_word_doc: If True, convert Word doc to Google Docs first
    
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
        # Step 0: Convert Word doc to Google Docs if needed
        original_doc_id = doc_id
        if is_word_doc:
            print(f"Converting Word document {doc_id} to Google Docs format...", file=sys.stderr)
            try:
                credentials = get_docs_credentials()
                doc_id = convert_word_to_google_doc(doc_id, credentials)
                print(f"Converted to Google Docs: {doc_id}", file=sys.stderr)
            except Exception as conv_error:
                error_msg = f"Failed to convert Word document to Google Docs: {str(conv_error)}"
                print(error_msg, file=sys.stderr)
                import traceback
                traceback.print_exc()
                return {
                    'success': False,
                    'error': error_msg,
                    'doc_id': original_doc_id,
                    'original_doc_id': original_doc_id
                }
        
        # Step 1: Extract text from document (now it's a Google Doc)
        print(f"Extracting text from document {doc_id}...", file=sys.stderr)
        credentials = get_docs_credentials()
        document_text = extract_text_from_doc(doc_id, credentials)
        
        if not document_text or len(document_text.strip()) < 10:
            return {
                'success': False,
                'error': 'Document appears to be empty or could not extract text',
                'doc_id': doc_id,
                'original_doc_id': original_doc_id if is_word_doc else None
            }
        
        # Step 2: Load rubric
        print(f"Loading rubric from {rubric_path}...", file=sys.stderr)
        rubric = load_rubric(str(rubric_path))
        
        # Step 3: Grade with AI
        print("Grading with AI...", file=sys.stderr)
        model_name = config.get('ai_model', {}).get('name', 'gemini-1.5-flash')
        grading_result = grade_with_ai(document_text, rubric, model_name, custom_instructions)
        
        # Step 4: Insert structured feedback text
        print("Inserting structured feedback...", file=sys.stderr)
        feedback_creds = get_feedback_credentials()
        feedback_success = insert_feedback_text(
            doc_id,
            grading_result.get('strengths', ''),
            grading_result.get('key_issues', ''),
            grading_result.get('suggestions', ''),
            feedback_creds,
            'Feedback'
        )
        
        if not feedback_success:
            print("Warning: Feedback text may not have been inserted correctly", file=sys.stderr)
        
        # Step 5: Insert rubric as formatted list
        print("Inserting rubric...", file=sys.stderr)
        rubric_creds = get_rubric_credentials()
        page_title = config.get('document', {}).get('rubric_page_title', 'Grading Rubric')
        rubric_success = insert_rubric_table(
            doc_id,
            rubric,
            grading_result.get('scores', {}),
            grading_result.get('total_score', 0),
            rubric_creds,
            page_title,
            grading_result.get('criterion_comments', {})
        )
        
        if not rubric_success:
            print("Warning: Rubric table may not have been inserted correctly", file=sys.stderr)
        
        # Step 6: Rename document to include "Graded"
        if feedback_success and rubric_success:
            print(f"Renaming document {doc_id} to include 'Graded'...", file=sys.stderr)
            try:
                rename_creds = get_docs_credentials()
                rename_success = rename_document_to_graded(doc_id, rename_creds)
                if not rename_success:
                    print("Warning: Document rename may have failed", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Could not rename document: {e}", file=sys.stderr)
        
        # Step 7: Delete original Word document if conversion was successful
        word_deleted = False
        if is_word_doc and feedback_success and rubric_success:
            print(f"Deleting original Word document {original_doc_id}...", file=sys.stderr)
            try:
                delete_creds = get_docs_credentials()
                word_deleted = delete_word_document(original_doc_id, delete_creds)
            except Exception as e:
                print(f"Warning: Could not delete original Word document: {e}", file=sys.stderr)
        
        # Return success result
        result = {
            'success': True,
            'doc_id': doc_id,  # The Google Doc ID (converted if was Word)
            'scores': grading_result.get('scores', {}),
            'total_score': grading_result.get('total_score', 0),
            'strengths': grading_result.get('strengths', ''),
            'key_issues': grading_result.get('key_issues', ''),
            'suggestions': grading_result.get('suggestions', ''),
            'feedback_inserted': feedback_success,
            'rubric_inserted': rubric_success
        }
        
        # Include original doc ID if it was converted
        if is_word_doc:
            result['original_doc_id'] = original_doc_id
            result['converted_doc_id'] = doc_id
            result['original_deleted'] = word_deleted
            if word_deleted:
                result['message'] = f'Word document converted, graded, and original deleted. Graded version: {doc_id}'
            else:
                result['message'] = f'Word document converted and graded. Graded version: {doc_id} (original not deleted)'
        
        return result
    
    except Exception as e:
        print(f"Error in grading workflow: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        error_result = {
            'success': False,
            'error': str(e),
            'doc_id': doc_id if 'doc_id' in locals() else original_doc_id if 'original_doc_id' in locals() else None
        }
        # Include original/converted IDs if they exist
        if is_word_doc and 'original_doc_id' in locals():
            error_result['original_doc_id'] = original_doc_id
            if 'doc_id' in locals() and doc_id != original_doc_id:
                error_result['converted_doc_id'] = doc_id
        return error_result


def grade_document_for_review(doc_id, rubric_path=None, config=None, custom_instructions=None, is_word_doc=False):
    """
    Grade a document for review workflow - does NOT update Google Docs.
    Only extracts text, grades with AI, and returns results.
    Google Docs will be updated later when session is approved.
    
    Args:
        doc_id: Google Docs document ID (or Word doc ID if is_word_doc=True)
        rubric_path: Path to rubric JSON file (optional, uses default from config)
        config: Configuration dictionary (optional)
        custom_instructions: Optional custom instructions for the AI grader
        is_word_doc: If True, convert Word doc to Google Docs first
    
    Returns:
        dict: Result with status, scores, document_text, and any errors
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
        # Step 0: Convert Word doc to Google Docs if needed
        original_doc_id = doc_id
        if is_word_doc:
            print(f"Converting Word document {doc_id} to Google Docs format...", file=sys.stderr)
            try:
                credentials = get_docs_credentials()
                doc_id = convert_word_to_google_doc(doc_id, credentials)
                print(f"Converted to Google Docs: {doc_id}", file=sys.stderr)
            except Exception as conv_error:
                error_msg = f"Failed to convert Word document to Google Docs: {str(conv_error)}"
                print(error_msg, file=sys.stderr)
                import traceback
                traceback.print_exc()
                return {
                    'success': False,
                    'error': error_msg,
                    'doc_id': original_doc_id,
                    'original_doc_id': original_doc_id
                }
        
        # Step 1: Extract text from document (now it's a Google Doc)
        print(f"Extracting text from document {doc_id}...", file=sys.stderr)
        credentials = get_docs_credentials()
        document_text = extract_text_from_doc(doc_id, credentials)
        
        if not document_text or len(document_text.strip()) < 10:
            return {
                'success': False,
                'error': 'Document appears to be empty or could not extract text',
                'doc_id': doc_id,
                'original_doc_id': original_doc_id if is_word_doc else None
            }
        
        # Step 2: Load rubric
        print(f"Loading rubric from {rubric_path}...", file=sys.stderr)
        rubric = load_rubric(str(rubric_path))
        
        # Step 3: Grade with AI
        print("Grading with AI...", file=sys.stderr)
        model_name = config.get('ai_model', {}).get('name', 'gemini-1.5-flash')
        grading_result = grade_with_ai(document_text, rubric, model_name, custom_instructions)
        
        # Return result WITHOUT updating Google Docs
        result = {
            'success': True,
            'doc_id': doc_id,  # The Google Doc ID (converted if was Word)
            'document_text': document_text,  # Include document text for review
            'scores': grading_result.get('scores', {}),
            'total_score': grading_result.get('total_score', 0),
            'strengths': grading_result.get('strengths', ''),
            'key_issues': grading_result.get('key_issues', ''),
            'suggestions': grading_result.get('suggestions', ''),
            'criterion_comments': grading_result.get('criterion_comments', {}),
            'rubric': rubric  # Include rubric for reference
        }
        
        # Include original doc ID if it was converted
        if is_word_doc:
            result['original_doc_id'] = original_doc_id
            result['converted_doc_id'] = doc_id
            result['message'] = f'Word document converted to Google Docs: {doc_id}'
        
        return result
    
    except Exception as e:
        print(f"Error in grading workflow: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        error_result = {
            'success': False,
            'error': str(e),
            'doc_id': doc_id if 'doc_id' in locals() else original_doc_id if 'original_doc_id' in locals() else None
        }
        # Include original/converted IDs if they exist
        if is_word_doc and 'original_doc_id' in locals():
            error_result['original_doc_id'] = original_doc_id
            if 'doc_id' in locals() and doc_id != original_doc_id:
                error_result['converted_doc_id'] = doc_id
        return error_result


def sync_feedback_to_document(doc_id, feedback_data, rubric=None, config=None):
    """
    Sync feedback and scores to Google Docs document.
    This is called when a grading session is approved.
    
    Args:
        doc_id: Google Docs document ID
        feedback_data: Dictionary with 'strengths', 'key_issues', 'suggestions', 'scores', 'total_score', 'criterion_comments'
        rubric: Rubric dictionary (optional, for rubric table)
        config: Configuration dictionary (optional)
    
    Returns:
        dict: Result with success status and any errors
    """
    if config is None:
        config = load_config()
    
    try:
        # Step 1: Insert structured feedback text
        print(f"Inserting structured feedback into document {doc_id}...", file=sys.stderr)
        feedback_creds = get_feedback_credentials()
        feedback_success = insert_feedback_text(
            doc_id,
            feedback_data.get('strengths', ''),
            feedback_data.get('key_issues', ''),
            feedback_data.get('suggestions', ''),
            feedback_creds,
            'Feedback'
        )
        
        if not feedback_success:
            print("Warning: Feedback text may not have been inserted correctly", file=sys.stderr)
        
        # Step 2: Insert rubric as formatted list (if rubric provided)
        rubric_success = True
        if rubric:
            print(f"Inserting rubric into document {doc_id}...", file=sys.stderr)
            rubric_creds = get_rubric_credentials()
            page_title = config.get('document', {}).get('rubric_page_title', 'Grading Rubric')
            rubric_success = insert_rubric_table(
                doc_id,
                rubric,
                feedback_data.get('scores', {}),
                feedback_data.get('total_score', 0),
                rubric_creds,
                page_title,
                feedback_data.get('criterion_comments', {})
            )
            
            if not rubric_success:
                print("Warning: Rubric table may not have been inserted correctly", file=sys.stderr)
        
        # Step 3: Rename document to include "Graded"
        if feedback_success and rubric_success:
            print(f"Renaming document {doc_id} to include 'Graded'...", file=sys.stderr)
            try:
                rename_creds = get_docs_credentials()
                rename_success = rename_document_to_graded(doc_id, rename_creds)
                if not rename_success:
                    print("Warning: Document rename may have failed", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Could not rename document: {e}", file=sys.stderr)
        
        return {
            'success': feedback_success and rubric_success,
            'feedback_inserted': feedback_success,
            'rubric_inserted': rubric_success if rubric else None,
            'doc_id': doc_id
        }
    
    except Exception as e:
        print(f"Error syncing feedback to document: {e}", file=sys.stderr)
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

