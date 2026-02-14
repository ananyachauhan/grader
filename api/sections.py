"""
Sections and Assignments API endpoints
"""
from flask import Blueprint, jsonify, request
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import get_db_session, Section, Assignment, User, GradingSession, AssignmentDocument

sections_bp = Blueprint('sections', __name__)

@sections_bp.route('/sections', methods=['GET'])
def list_sections():
    """List all sections"""
    session = get_db_session()
    try:
        sections = session.query(Section).all()
        return jsonify({
            'sections': [{
                'id': s.id,
                'section_number': s.section_number,
                'course_code': s.course_code,
                'assignment_count': len(s.assignments)
            } for s in sections]
        })
    finally:
        session.close()

@sections_bp.route('/sections/<int:section_id>/assignments', methods=['GET'])
def list_assignments(section_id):
    """List assignments for a section"""
    session = get_db_session()
    try:
        section = session.query(Section).filter_by(id=section_id).first()
        if not section:
            return jsonify({'error': 'Section not found'}), 404
        
        assignments = session.query(Assignment).filter_by(section_id=section_id).order_by(Assignment.created_at.desc()).all()
        
        return jsonify({
            'assignments': [{
                'id': a.id,
                'name': a.name,
                'description': a.description,
                'status': a.status,
                'rubric_filename': a.rubric_filename,
                'drive_folder_id': a.drive_folder_id,
                'created_at': a.created_at.isoformat() if a.created_at else None,
                'activated_at': a.activated_at.isoformat() if a.activated_at else None,
                'completed_at': a.completed_at.isoformat() if a.completed_at else None,
                'created_by': a.created_by
            } for a in assignments]
        })
    finally:
        session.close()

@sections_bp.route('/sections/<int:section_id>/assignments', methods=['POST'])
def create_assignment(section_id):
    """Create a new assignment"""
    data = request.json
    session = get_db_session()
    try:
        section = session.query(Section).filter_by(id=section_id).first()
        if not section:
            return jsonify({'error': 'Section not found'}), 404
        
        # Get or create user (simplified - in production, use proper auth)
        user_email = data.get('user_email', 'admin@busn403.edu')
        user = session.query(User).filter_by(email=user_email).first()
        if not user:
            user = User(
                email=user_email,
                name=data.get('user_name', 'User'),
                role=data.get('user_role', 'ta')
            )
            session.add(user)
            session.flush()
        
        assignment = Assignment(
            section_id=section_id,
            name=data['name'],
            description=data.get('description', ''),
            rubric_filename=data['rubric_filename'],
            custom_instructions=data.get('custom_instructions', ''),
            drive_folder_id=data['drive_folder_id'],
            status=data.get('status', 'draft'),
            created_by=user.id
        )
        
        session.add(assignment)
        session.commit()
        
        return jsonify({
            'success': True,
            'assignment': {
                'id': assignment.id,
                'name': assignment.name,
                'status': assignment.status
            }
        }), 201
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@sections_bp.route('/assignments/<int:assignment_id>', methods=['GET'])
def get_assignment(assignment_id):
    """Get assignment details"""
    session = get_db_session()
    try:
        assignment = session.query(Assignment).filter_by(id=assignment_id).first()
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        return jsonify({
            'assignment': {
                'id': assignment.id,
                'section_id': assignment.section_id,
                'name': assignment.name,
                'description': assignment.description,
                'status': assignment.status,
                'rubric_filename': assignment.rubric_filename,
                'custom_instructions': assignment.custom_instructions,
                'drive_folder_id': assignment.drive_folder_id,
                'created_at': assignment.created_at.isoformat() if assignment.created_at else None,
                'activated_at': assignment.activated_at.isoformat() if assignment.activated_at else None,
                'completed_at': assignment.completed_at.isoformat() if assignment.completed_at else None,
                'created_by': assignment.created_by
            }
        })
    finally:
        session.close()

@sections_bp.route('/assignments/<int:assignment_id>', methods=['PUT'])
def update_assignment(assignment_id):
    """Update an assignment"""
    data = request.json
    session = get_db_session()
    try:
        assignment = session.query(Assignment).filter_by(id=assignment_id).first()
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        # Update fields
        if 'name' in data:
            assignment.name = data['name']
        if 'description' in data:
            assignment.description = data['description']
        if 'rubric_filename' in data:
            assignment.rubric_filename = data['rubric_filename']
        if 'custom_instructions' in data:
            assignment.custom_instructions = data['custom_instructions']
        if 'drive_folder_id' in data:
            assignment.drive_folder_id = data['drive_folder_id']
        if 'status' in data:
            new_status = data['status']
            if new_status == 'active' and assignment.status == 'draft':
                assignment.activated_at = datetime.utcnow()
            elif new_status == 'completed' and assignment.status != 'completed':
                assignment.completed_at = datetime.utcnow()
            assignment.status = new_status
        
        session.commit()
        
        return jsonify({
            'success': True,
            'assignment': {
                'id': assignment.id,
                'name': assignment.name,
                'status': assignment.status
            }
        })
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@sections_bp.route('/assignments/<int:assignment_id>', methods=['DELETE'])
def delete_assignment(assignment_id):
    """Delete an assignment"""
    session = get_db_session()
    try:
        assignment = session.query(Assignment).filter_by(id=assignment_id).first()
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        assignment_name = assignment.name
        
        # Use raw SQL to delete related records to avoid SQLAlchemy relationship issues
        # Delete grading sessions using raw SQL
        session.execute(
            text("DELETE FROM grading_sessions WHERE assignment_id = :assignment_id"),
            {'assignment_id': assignment_id}
        )
        
        # Delete assignment documents using raw SQL
        session.execute(
            text("DELETE FROM assignment_documents WHERE assignment_id = :assignment_id"),
            {'assignment_id': assignment_id}
        )
        
        # Now delete the assignment
        session.delete(assignment)
        session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Assignment "{assignment_name}" deleted successfully'
        })
    except Exception as e:
        session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error deleting assignment: {error_trace}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

def generate_fallback_summary(all_feedback):
    """Generate a simple summary from feedback patterns when AI is not available"""
    if not all_feedback:
        return "No grading data is available yet."
    
    # Extract common themes from actual feedback text
    all_strengths = [f['strengths'] for f in all_feedback if f.get('strengths')]
    all_issues = [f['key_issues'] for f in all_feedback if f.get('key_issues')]
    all_suggestions = [f['suggestions'] for f in all_feedback if f.get('suggestions')]
    
    summary = f"Based on feedback from {len(all_feedback)} student assignments, "
    
    if all_strengths:
        summary += "students demonstrated various strengths across their submissions. "
    else:
        summary += "the assignments showed areas that need improvement. "
    
    if all_issues:
        summary += "Common issues identified in the feedback include areas that require additional attention. "
    
    if all_suggestions:
        summary += "The feedback suggests several areas for improvement across the class. "
    
    summary += "Overall, the feedback indicates a range of performance levels across the class."
    
    return summary

@sections_bp.route('/assignments/<int:assignment_id>/documents', methods=['GET'])
def get_assignment_documents(assignment_id):
    """Get all documents for an assignment with their status and session info.
    Also syncs documents from Google Drive folder if they're not in the database yet."""
    session = get_db_session()
    try:
        assignment = session.query(Assignment).filter_by(id=assignment_id).first()
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        # If assignment has a drive folder, sync documents from Drive
        if assignment.drive_folder_id:
            try:
                # Import documents API to list files
                from api.documents import get_drive_service
                service = get_drive_service()
                
                # Query for documents in the folder
                query = f"'{assignment.drive_folder_id}' in parents and (mimeType='application/vnd.google-apps.document' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document' or mimeType='application/msword') and trashed=false"
                
                results = service.files().list(
                    q=query,
                    fields="files(id, name, mimeType)",
                    orderBy="modifiedTime desc"
                ).execute()
                
                # Create or update document records
                for file in results.get('files', []):
                    doc_id = file['id']
                    doc_name = file['name']
                    
                    # Check if document already exists
                    existing_doc = session.query(AssignmentDocument).filter_by(
                        assignment_id=assignment_id,
                        doc_id=doc_id
                    ).first()
                    
                    if not existing_doc:
                        # Create new document record with 'ungraded' status
                        new_doc = AssignmentDocument(
                            assignment_id=assignment_id,
                            doc_id=doc_id,
                            doc_name=doc_name,
                            status='ungraded'
                        )
                        session.add(new_doc)
                
                session.commit()
            except Exception as e:
                # If Drive sync fails, continue with existing documents
                print(f"Warning: Could not sync documents from Drive: {e}", flush=True)
                session.rollback()
        
        # Get all documents for this assignment
        documents = session.query(AssignmentDocument).filter_by(assignment_id=assignment_id).all()
        
        # Get all grading sessions for this assignment to find which session each document belongs to
        sessions = session.query(GradingSession).filter_by(assignment_id=assignment_id).order_by(GradingSession.created_at.desc()).all()
        
        # Build a map of doc_id to session info
        doc_to_session = {}
        for grading_session in sessions:
            try:
                doc_ids = json.loads(grading_session.doc_ids) if grading_session.doc_ids else []
                results = json.loads(grading_session.results) if grading_session.results else []
                
                for idx, doc_id in enumerate(doc_ids):
                    if doc_id not in doc_to_session:
                        # Get the result for this document
                        result = results[idx] if idx < len(results) else None
                        doc_to_session[doc_id] = {
                            'session_id': grading_session.id,
                            'doc_index': idx,
                            'session_status': grading_session.status,
                            'result': result
                        }
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        # Build response
        documents_list = []
        for doc in documents:
            session_info = doc_to_session.get(doc.doc_id, {})
            documents_list.append({
                'id': doc.id,
                'doc_id': doc.doc_id,
                'doc_name': doc.doc_name,
                'status': doc.status,
                'graded_at': doc.graded_at.isoformat() if doc.graded_at else None,
                'reviewed_at': doc.reviewed_at.isoformat() if doc.reviewed_at else None,
                'session_id': session_info.get('session_id'),
                'doc_index': session_info.get('doc_index'),
                'session_status': session_info.get('session_status'),
                'assignment_id': assignment_id,
                'assignment_name': assignment.name
            })
        
        return jsonify({
            'documents': documents_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@sections_bp.route('/assignments/<int:assignment_id>/history', methods=['GET'])
def get_grading_history(assignment_id):
    """Get grading history for an assignment"""
    session = get_db_session()
    try:
        assignment = session.query(Assignment).filter_by(id=assignment_id).first()
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        sessions = session.query(GradingSession).filter_by(assignment_id=assignment_id).order_by(GradingSession.created_at.desc()).all()
        
        return jsonify({
            'history': [{
                'id': s.id,
                'graded_by': s.graded_by,
                'doc_ids': json.loads(s.doc_ids),
                'status': s.status,
                'reviewed_by': s.reviewed_by,
                'reviewed_at': s.reviewed_at.isoformat() if s.reviewed_at else None,
                'created_at': s.created_at.isoformat() if s.created_at else None
            } for s in sessions]
        })
    finally:
        session.close()


@sections_bp.route('/assignments/<int:assignment_id>/summary', methods=['GET'])
def get_assignment_summary(assignment_id):
    """Get grading summary statistics for an assignment"""
    session = get_db_session()
    try:
        assignment = session.query(Assignment).filter_by(id=assignment_id).first()
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        # Get all grading sessions for this assignment
        sessions = session.query(GradingSession).filter_by(assignment_id=assignment_id).all()
        
        # Collect all scores from all sessions
        all_scores = []
        total_documents = 0
        graded_documents = 0
        
        for grading_session in sessions:
            try:
                results = json.loads(grading_session.results)
                if isinstance(results, list):
                    for result in results:
                        if result.get('success') and 'total_score' in result:
                            all_scores.append(result['total_score'])
                            graded_documents += 1
                        total_documents += 1
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        # Calculate statistics
        if all_scores:
            avg_score = sum(all_scores) / len(all_scores)
            min_score = min(all_scores)
            max_score = max(all_scores)
            
            # Calculate grade distribution
            # Get total points from rubric (supports Fly.io persistent storage)
            import os
            fly_volume_path = os.getenv('FLY_VOLUME_PATH', '/data')
            rubric_path = Path(fly_volume_path) / 'rubrics' / assignment.rubric_filename
            
            # Fallback to local path for development
            if not rubric_path.parent.exists():
                rubric_path = Path(__file__).parent.parent / 'rubrics' / assignment.rubric_filename
            
            total_points = 100  # Default
            if rubric_path.exists():
                try:
                    with open(rubric_path, 'r', encoding='utf-8') as f:
                        rubric_data = json.load(f)
                        total_points = rubric_data.get('total_points', 100)
                except Exception as e:
                    print(f"Error loading rubric for summary: {e}", flush=True)
                    pass
            
            # Grade distribution
            a_count = sum(1 for s in all_scores if s >= total_points * 0.9)
            b_count = sum(1 for s in all_scores if total_points * 0.8 <= s < total_points * 0.9)
            c_count = sum(1 for s in all_scores if total_points * 0.7 <= s < total_points * 0.8)
            d_count = sum(1 for s in all_scores if total_points * 0.6 <= s < total_points * 0.7)
            f_count = sum(1 for s in all_scores if s < total_points * 0.6)
        else:
            avg_score = 0
            min_score = 0
            max_score = 0
            a_count = b_count = c_count = d_count = f_count = 0
        
        # Get document status counts
        documents = session.query(AssignmentDocument).filter_by(assignment_id=assignment_id).all()
        ungraded_count = sum(1 for d in documents if d.status == 'ungraded')
        graded_count = sum(1 for d in documents if d.status == 'graded')
        reviewed_count = sum(1 for d in documents if d.status == 'reviewed')
        
        # Collect all feedback from grading results
        all_feedback = []
        for grading_session in sessions:
            try:
                results = json.loads(grading_session.results)
                if isinstance(results, list):
                    for result in results:
                        if result.get('success'):
                            feedback_item = {
                                'strengths': result.get('strengths', ''),
                                'key_issues': result.get('key_issues', ''),
                                'suggestions': result.get('suggestions', '')
                            }
                            if any(feedback_item.values()):  # Only add if there's actual feedback
                                all_feedback.append(feedback_item)
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        # Generate subjective performance summary based on actual feedback
        performance_summary = ""
        if all_feedback:
            # Use AI to analyze all feedback and generate a subjective summary
            try:
                import os
                from dotenv import load_dotenv
                import google.generativeai as genai
                
                # Load API key
                env_path = Path(__file__).parent.parent / '.env'
                if env_path.exists():
                    load_dotenv(dotenv_path=env_path, override=True)
                
                api_key = os.getenv('GEMINI_API_KEY')
                if api_key:
                    api_key = api_key.strip()
                    genai.configure(api_key=api_key)
                    
                    # Prepare feedback text for analysis
                    feedback_text = ""
                    for i, feedback in enumerate(all_feedback, 1):
                        feedback_text += f"\n\nAssignment {i}:\n"
                        if feedback['strengths']:
                            feedback_text += f"Strengths: {feedback['strengths']}\n"
                        if feedback['key_issues']:
                            feedback_text += f"Key Issues: {feedback['key_issues']}\n"
                        if feedback['suggestions']:
                            feedback_text += f"Suggestions: {feedback['suggestions']}\n"
                    
                    # Generate summary using AI
                    prompt = f"""You are analyzing feedback from grading {len(all_feedback)} student assignments. Based on the actual feedback provided for each student, write a brief paragraph (3-4 sentences) summarizing how the class performed overall. Focus on:

1. Common strengths across students based on the feedback
2. Common issues or areas of difficulty mentioned in the feedback
3. Overall assessment of student performance based on the actual comments

Be subjective and descriptive based on the actual feedback text, not just metrics. Write as if you're a professor summarizing class performance based on the detailed feedback given to each student.

Feedback from all students:
{feedback_text}

Write a concise, subjective summary paragraph based on this feedback:"""
                    
                    # Try to find an available model
                    try:
                        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        model_name = None
                        for preferred in ["models/gemini-2.5-flash", "models/gemini-flash-latest", "models/gemini-pro-latest"]:
                            if preferred in available_models:
                                model_name = preferred
                                break
                        if not model_name and available_models:
                            model_name = available_models[0]
                        
                        if model_name:
                            model = genai.GenerativeModel(model_name=model_name)
                            response = model.generate_content(prompt)
                            performance_summary = response.text.strip()
                        else:
                            raise ValueError("No available models")
                    except Exception as e:
                        # Fallback: generate simple summary from feedback patterns
                        performance_summary = generate_fallback_summary(all_feedback)
                else:
                    # Fallback: generate simple summary from feedback patterns
                    performance_summary = generate_fallback_summary(all_feedback)
            except Exception as e:
                # Fallback: generate simple summary from feedback patterns
                performance_summary = generate_fallback_summary(all_feedback)
        else:
            performance_summary = "No grading data is available yet. Once documents are graded, a performance summary will be generated based on the feedback provided to each student."
        
        return jsonify({
            'summary': {
                'total_documents': len(documents),
                'graded_documents': graded_documents,
                'ungraded_documents': ungraded_count,
                'reviewed_documents': reviewed_count,
                'average_score': round(avg_score, 2) if all_scores else None,
                'min_score': min_score if all_scores else None,
                'max_score': max_score if all_scores else None,
                'total_points': total_points,
                'grade_distribution': {
                    'A': a_count,
                    'B': b_count,
                    'C': c_count,
                    'D': d_count,
                    'F': f_count
                },
                'performance_summary': performance_summary
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@sections_bp.route('/sessions', methods=['POST'])
def create_grading_session():
    """Save a grading session"""
    data = request.json
    session = get_db_session()
    try:
        assignment_id = data.get('assignment_id')
        assignment = session.query(Assignment).filter_by(id=assignment_id).first()
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        # Get or create user
        user_email = data.get('user_email', 'admin@busn403.edu')
        user = session.query(User).filter_by(email=user_email).first()
        if not user:
            user = User(
                email=user_email,
                name=data.get('user_name', 'User'),
                role=data.get('user_role', 'ta')
            )
            session.add(user)
            session.flush()
        
        # Create grading session
        grading_session = GradingSession(
            assignment_id=assignment_id,
            graded_by=user.id,
            doc_ids=json.dumps(data.get('doc_ids', [])),
            results=json.dumps(data.get('results', [])),
            status='pending_review'
        )
        
        session.add(grading_session)
        
        # Update document statuses to 'pending_review' after grading
        for doc_id in data.get('doc_ids', []):
            doc = session.query(AssignmentDocument).filter_by(
                assignment_id=assignment_id,
                doc_id=doc_id
            ).first()
            
            if doc:
                doc.status = 'pending_review'
                doc.graded_at = datetime.utcnow()
            else:
                # Create document record if it doesn't exist
                doc = AssignmentDocument(
                    assignment_id=assignment_id,
                    doc_id=doc_id,
                    doc_name=f"Document {doc_id}",  # Could be improved
                    status='pending_review',
                    graded_at=datetime.utcnow()
                )
                session.add(doc)
        
        session.commit()
        
        return jsonify({
            'success': True,
            'session_id': grading_session.id,
            'message': 'Grading session saved successfully'
        }), 201
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@sections_bp.route('/sessions/<int:session_id>', methods=['GET'])
def get_grading_session(session_id):
    """Get detailed information about a grading session"""
    session = get_db_session()
    try:
        grading_session = session.query(GradingSession).filter_by(id=session_id).first()
        if not grading_session:
            return jsonify({'error': 'Grading session not found'}), 404
        
        assignment = session.query(Assignment).filter_by(id=grading_session.assignment_id).first()
        grader = session.query(User).filter_by(id=grading_session.graded_by).first()
        reviewer = session.query(User).filter_by(id=grading_session.reviewed_by).first() if grading_session.reviewed_by else None
        
        results = json.loads(grading_session.results) if grading_session.results else []
        doc_ids = json.loads(grading_session.doc_ids) if grading_session.doc_ids else []
        
        # Load rubric for the assignment
        rubric = None
        if assignment and assignment.rubric_filename:
            import os
            fly_volume_path = os.getenv('FLY_VOLUME_PATH', '/data')
            rubric_path = Path(fly_volume_path) / 'rubrics' / assignment.rubric_filename
            if not rubric_path.parent.exists():
                rubric_path = Path(__file__).parent.parent / 'rubrics' / assignment.rubric_filename
            
            if rubric_path.exists():
                try:
                    sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
                    from ai_grader import load_rubric
                    rubric = load_rubric(str(rubric_path))
                except Exception as e:
                    print(f"Error loading rubric: {e}", flush=True)
        
        return jsonify({
            'id': grading_session.id,
            'assignment_id': grading_session.assignment_id,
            'assignment_name': assignment.name if assignment else None,
            'graded_by': {
                'id': grader.id if grader else None,
                'name': grader.name if grader else None,
                'email': grader.email if grader else None
            },
            'doc_ids': doc_ids,
            'results': results,
            'rubric': rubric,  # Include rubric for score editing
            'status': grading_session.status,
            'reviewed_by': {
                'id': reviewer.id if reviewer else None,
                'name': reviewer.name if reviewer else None,
                'email': reviewer.email if reviewer else None
            } if reviewer else None,
            'reviewed_at': grading_session.reviewed_at.isoformat() if grading_session.reviewed_at else None,
            'review_notes': grading_session.review_notes,
            'created_at': grading_session.created_at.isoformat() if grading_session.created_at else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@sections_bp.route('/sessions/<int:session_id>/approve', methods=['POST'])
def approve_grading_session(session_id):
    """Approve a grading session and sync feedback to Google Docs"""
    data = request.json or {}
    session = get_db_session()
    
    try:
        grading_session = session.query(GradingSession).filter_by(id=session_id).first()
        if not grading_session:
            return jsonify({'error': 'Grading session not found'}), 404
        
        if grading_session.status != 'pending_review':
            return jsonify({'error': f'Session is not pending review (current status: {grading_session.status})'}), 400
        
        # Get or create reviewer user
        user_email = data.get('user_email', 'admin@busn403.edu')
        reviewer = session.query(User).filter_by(email=user_email).first()
        if not reviewer:
            reviewer = User(
                email=user_email,
                name=data.get('user_name', 'Reviewer'),
                role=data.get('user_role', 'professor')
            )
            session.add(reviewer)
            session.flush()
        
        # Get edited results if provided, otherwise use original
        edited_results = data.get('results', None)
        if edited_results:
            # Update results with edited feedback
            grading_session.results = json.dumps(edited_results)
        
        # Get assignment and rubric
        assignment = session.query(Assignment).filter_by(id=grading_session.assignment_id).first()
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        # Load rubric
        import os
        fly_volume_path = os.getenv('FLY_VOLUME_PATH', '/data')
        rubric_path = Path(fly_volume_path) / 'rubrics' / assignment.rubric_filename
        if not rubric_path.parent.exists():
            rubric_path = Path(__file__).parent.parent / 'rubrics' / assignment.rubric_filename
        
        if not rubric_path.exists():
            return jsonify({'error': f'Rubric not found: {assignment.rubric_filename}'}), 404
        
        # Import grading workflow for sync function
        sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
        from grading_workflow import sync_feedback_to_document, load_rubric, load_config
        
        rubric = load_rubric(str(rubric_path))
        config = load_config()
        
        # Get results (edited or original)
        results = edited_results if edited_results else json.loads(grading_session.results)
        doc_ids = json.loads(grading_session.doc_ids)
        
        # Sync feedback to each document
        sync_results = []
        for result in results:
            if not result.get('success'):
                sync_results.append({
                    'doc_id': result.get('doc_id'),
                    'success': False,
                    'error': result.get('error', 'Grading failed')
                })
                continue
            
            doc_id = result.get('converted_doc_id') or result.get('doc_id')
            if not doc_id:
                sync_results.append({
                    'doc_id': result.get('doc_id'),
                    'success': False,
                    'error': 'No document ID found'
                })
                continue
            
            # Prepare feedback data
            feedback_data = {
                'strengths': result.get('strengths', ''),
                'key_issues': result.get('key_issues', ''),
                'suggestions': result.get('suggestions', ''),
                'scores': result.get('scores', {}),
                'total_score': result.get('total_score', 0),
                'criterion_comments': result.get('criterion_comments', {})
            }
            
            # Sync to Google Docs
            sync_result = sync_feedback_to_document(doc_id, feedback_data, rubric, config)
            sync_results.append(sync_result)
            
            # Update document status
            doc = session.query(AssignmentDocument).filter_by(
                assignment_id=grading_session.assignment_id,
                doc_id=doc_id
            ).first()
            
            if doc:
                doc.status = 'reviewed'
            else:
                doc = AssignmentDocument(
                    assignment_id=grading_session.assignment_id,
                    doc_id=doc_id,
                    doc_name=f"Document {doc_id}",
                    status='reviewed'
                )
                session.add(doc)
        
        # Update session status
        grading_session.status = 'approved'
        grading_session.reviewed_by = reviewer.id
        grading_session.reviewed_at = datetime.utcnow()
        grading_session.review_notes = data.get('review_notes', '').strip() or None
        
        session.commit()
        
        return jsonify({
            'success': True,
            'session_id': grading_session.id,
            'sync_results': sync_results,
            'message': 'Grading session approved and feedback synced to Google Docs'
        }), 200
        
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@sections_bp.route('/sessions/<int:session_id>/reject', methods=['POST'])
def reject_grading_session(session_id):
    """Reject a grading session"""
    data = request.json or {}
    session = get_db_session()
    
    try:
        grading_session = session.query(GradingSession).filter_by(id=session_id).first()
        if not grading_session:
            return jsonify({'error': 'Grading session not found'}), 404
        
        if grading_session.status != 'pending_review':
            return jsonify({'error': f'Session is not pending review (current status: {grading_session.status})'}), 400
        
        # Get or create reviewer user
        user_email = data.get('user_email', 'admin@busn403.edu')
        reviewer = session.query(User).filter_by(email=user_email).first()
        if not reviewer:
            reviewer = User(
                email=user_email,
                name=data.get('user_name', 'Reviewer'),
                role=data.get('user_role', 'professor')
            )
            session.add(reviewer)
            session.flush()
        
        # Update session status
        grading_session.status = 'rejected'
        grading_session.reviewed_by = reviewer.id
        grading_session.reviewed_at = datetime.utcnow()
        grading_session.review_notes = data.get('review_notes', '').strip() or None
        
        # Reset document statuses back to 'ungraded'
        doc_ids = json.loads(grading_session.doc_ids) if grading_session.doc_ids else []
        for doc_id in doc_ids:
            doc = session.query(AssignmentDocument).filter_by(
                assignment_id=grading_session.assignment_id,
                doc_id=doc_id
            ).first()
            if doc:
                doc.status = 'ungraded'
        
        session.commit()
        
        return jsonify({
            'success': True,
            'session_id': grading_session.id,
            'message': 'Grading session rejected'
        }), 200
        
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@sections_bp.route('/sessions/<int:session_id>/approve-document', methods=['POST'])
def approve_document(session_id):
    """Approve a single document from a grading session and sync feedback to Google Docs"""
    data = request.json or {}
    session = get_db_session()
    
    try:
        grading_session = session.query(GradingSession).filter_by(id=session_id).first()
        if not grading_session:
            return jsonify({'error': 'Grading session not found'}), 404
        
        doc_index = data.get('doc_index')
        if doc_index is None:
            return jsonify({'error': 'doc_index is required'}), 400
        
        # Get results and doc_ids
        results = json.loads(grading_session.results) if grading_session.results else []
        doc_ids = json.loads(grading_session.doc_ids) if grading_session.doc_ids else []
        
        if doc_index >= len(results) or doc_index >= len(doc_ids):
            return jsonify({'error': 'Invalid doc_index'}), 400
        
        # Get the specific result
        result = data.get('result')
        if not result:
            result = results[doc_index]
        
        if not result.get('success'):
            return jsonify({'error': 'Document grading failed, cannot approve'}), 400
        
        # Get or create reviewer user
        user_email = data.get('user_email', 'admin@busn403.edu')
        reviewer = session.query(User).filter_by(email=user_email).first()
        if not reviewer:
            reviewer = User(
                email=user_email,
                name=data.get('user_name', 'Reviewer'),
                role=data.get('user_role', 'professor')
            )
            session.add(reviewer)
            session.flush()
        
        # Update the result in the results array
        results[doc_index] = result
        grading_session.results = json.dumps(results)
        
        # Get assignment and rubric
        assignment = session.query(Assignment).filter_by(id=grading_session.assignment_id).first()
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        # Load rubric
        import os
        fly_volume_path = os.getenv('FLY_VOLUME_PATH', '/data')
        rubric_path = Path(fly_volume_path) / 'rubrics' / assignment.rubric_filename
        if not rubric_path.parent.exists():
            rubric_path = Path(__file__).parent.parent / 'rubrics' / assignment.rubric_filename
        
        if not rubric_path.exists():
            return jsonify({'error': f'Rubric not found: {assignment.rubric_filename}'}), 404
        
        # Import grading workflow for sync function
        sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
        from grading_workflow import sync_feedback_to_document, load_rubric, load_config
        
        rubric = load_rubric(str(rubric_path))
        config = load_config()
        
        # Get document ID
        doc_id = result.get('converted_doc_id') or result.get('doc_id')
        if not doc_id:
            return jsonify({'error': 'No document ID found in result'}), 400
        
        # Prepare feedback data
        feedback_data = {
            'strengths': result.get('strengths', ''),
            'key_issues': result.get('key_issues', ''),
            'suggestions': result.get('suggestions', ''),
            'scores': result.get('scores', {}),
            'total_score': result.get('total_score', 0),
            'criterion_comments': result.get('criterion_comments', {})
        }
        
        # Sync to Google Docs
        sync_result = sync_feedback_to_document(doc_id, feedback_data, rubric, config)
        
        if not sync_result.get('success'):
            return jsonify({'error': f'Failed to sync to Google Docs: {sync_result.get("error", "Unknown error")}'}), 500
        
        # Update document status to 'reviewed'
        doc = session.query(AssignmentDocument).filter_by(
            assignment_id=grading_session.assignment_id,
            doc_id=doc_id
        ).first()
        
        if doc:
            doc.status = 'reviewed'
            doc.reviewed_at = datetime.utcnow()
        else:
            doc = AssignmentDocument(
                assignment_id=grading_session.assignment_id,
                doc_id=doc_id,
                doc_name=f"Document {doc_id}",
                status='reviewed',
                reviewed_at=datetime.utcnow()
            )
            session.add(doc)
        
        # Check if all documents in session are reviewed - if so, mark session as approved
        all_reviewed = True
        for did in doc_ids:
            doc_check = session.query(AssignmentDocument).filter_by(
                assignment_id=grading_session.assignment_id,
                doc_id=did
            ).first()
            if not doc_check or doc_check.status != 'reviewed':
                all_reviewed = False
                break
        
        if all_reviewed:
            grading_session.status = 'approved'
            if not grading_session.reviewed_by:
                grading_session.reviewed_by = reviewer.id
            if not grading_session.reviewed_at:
                grading_session.reviewed_at = datetime.utcnow()
        
        session.commit()
        
        return jsonify({
            'success': True,
            'session_id': grading_session.id,
            'doc_index': doc_index,
            'sync_result': sync_result,
            'message': 'Document approved and feedback synced to Google Docs'
        }), 200
        
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@sections_bp.route('/sessions/<int:session_id>/reject-document', methods=['POST'])
def reject_document(session_id):
    """Reject a single document from a grading session"""
    data = request.json or {}
    session = get_db_session()
    
    try:
        grading_session = session.query(GradingSession).filter_by(id=session_id).first()
        if not grading_session:
            return jsonify({'error': 'Grading session not found'}), 404
        
        doc_index = data.get('doc_index')
        if doc_index is None:
            return jsonify({'error': 'doc_index is required'}), 400
        
        # Get doc_ids
        doc_ids = json.loads(grading_session.doc_ids) if grading_session.doc_ids else []
        
        if doc_index >= len(doc_ids):
            return jsonify({'error': 'Invalid doc_index'}), 400
        
        # Get or create reviewer user
        user_email = data.get('user_email', 'admin@busn403.edu')
        reviewer = session.query(User).filter_by(email=user_email).first()
        if not reviewer:
            reviewer = User(
                email=user_email,
                name=data.get('user_name', 'Reviewer'),
                role=data.get('user_role', 'professor')
            )
            session.add(reviewer)
            session.flush()
        
        # Get document ID
        doc_id = doc_ids[doc_index]
        
        # Update document status back to 'ungraded'
        doc = session.query(AssignmentDocument).filter_by(
            assignment_id=grading_session.assignment_id,
            doc_id=doc_id
        ).first()
        
        if doc:
            doc.status = 'ungraded'
            doc.graded_at = None
        
        session.commit()
        
        return jsonify({
            'success': True,
            'session_id': grading_session.id,
            'doc_index': doc_index,
            'message': 'Document rejected'
        }), 200
        
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

