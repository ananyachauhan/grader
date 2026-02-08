# BUSN 403 Grading Platform

Course-specific grading platform for BUSN 403 - Business Writing and Communication.

## Features

- **Section Management**: Three sections (900, 901, 902)
- **Assignment Management**: Create, edit, delete assignments per section
- **Rubric Management**: Upload/select rubrics for each assignment
- **Custom Instructions**: Add assignment-specific grading instructions
- **Google Drive Integration**: Connect Drive folders for ungraded assignments
- **Status Workflow**: Draft → Active → Completed (with review)
- **Grading History**: Track all grading sessions per assignment
- **Review System**: Grading sessions require review before completion

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Set up your `.env` file in `config/` folder with:
- `GOOGLE_API_KEY` or `GOOGLE_CREDENTIALS_PATH`
- `GEMINI_API_KEY`

### 3. Run the Application

```bash
python app.py
```

The database (`busn403_grading.db`) will be created automatically with default sections.

### 4. Access the Platform

Open `http://localhost:5000` in your browser.

## User Flow

1. **Select Section**: Choose section 900, 901, or 902
2. **View/Create Assignments**: See existing assignments or create new ones
3. **Configure Assignment**:
   - Name and description
   - Select/upload rubric
   - Add custom grading instructions (optional)
   - Connect Google Drive folder with student submissions
   - Set status (Draft/Active/Completed)
4. **Grade Assignment**:
   - Load documents from connected Drive folder
   - Select documents to grade
   - AI grades and inserts comments/scores
   - Review results
   - Save for review
5. **Review & Complete**: Review grading sessions and mark assignment as completed

## Database Structure

- **Sections**: Course sections (900, 901, 902)
- **Assignments**: Writing assignments per section
- **Users**: Professors and TAs
- **Grading Sessions**: History of all grading activities
- **Assignment Documents**: Track document status per assignment

## Status Workflow

- **Draft**: Assignment being set up
- **Active**: Ready for grading
- **Completed**: All grading reviewed and finished

## Grading Session Status

- **pending_review**: Grading completed, awaiting human review
- **approved**: Review completed and approved
- **rejected**: Review rejected (needs re-grading)

## Notes

- All professors and TAs share the same assignments per section
- Both professors and TAs can create assignments
- Grading sessions are saved with status "pending_review"
- Review workflow allows human oversight before marking complete

