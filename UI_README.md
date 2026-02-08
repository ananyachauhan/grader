# AI Grading System - Web UI

A web-based user interface for the AI Grading System that allows you to grade multiple writing assignments with a simple, intuitive interface.

## Features

- 🎯 **Select Rubric**: Choose from available rubrics
- 📁 **Load Documents**: Browse and select Google Docs from a Drive folder
- ✅ **Batch Grading**: Grade multiple documents at once
- 📊 **Results Dashboard**: View statistics and results
- 🔍 **Search & Filter**: Find specific documents quickly
- 📤 **Export Results**: Download grading results as CSV

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Make sure your `.env` file in the `config/` folder has:
- `GOOGLE_API_KEY` or `GOOGLE_CREDENTIALS_PATH`
- `GEMINI_API_KEY`
- `GOOGLE_DRIVE_FOLDER_ID` (optional, can enter in UI)

### 3. Run the Application

```bash
python app.py
```

The web interface will be available at: **http://localhost:5000**

## Usage

1. **Select Rubric**: Choose a rubric from the dropdown
2. **Load Documents**: 
   - Enter a Google Drive folder ID (or use default from `.env`)
   - Click "Load Documents" to see all Google Docs in that folder
3. **Select Documents**: Check the documents you want to grade
4. **Grade**: Click "Grade Selected Documents"
   - The AI will automatically grade and insert comments/scores
5. **Review Results**: 
   - View statistics and results in the dashboard
   - Click "Open" to view any graded document
   - Use "Open All in Drive" to review all documents
   - Export results to CSV if needed

## Workflow

The UI follows the simplified workflow:
- **Auto-Insert**: AI grades and immediately inserts comments/scores into documents
- **Post-Grading Review**: You can then open each document to review and add your own comments
- **No Pre-Review**: This saves time - you review after insertion, not before

## API Endpoints

- `GET /api/grading/rubrics` - List available rubrics
- `POST /api/grading/grade` - Grade a single document
- `POST /api/grading/grade/batch` - Grade multiple documents
- `GET /api/documents/list?folder_id=XXX` - List documents in folder

## Notes

- Documents are graded automatically and comments/scores are inserted immediately
- You can review and add your own comments after grading
- The dashboard shows all results for easy tracking
- All graded documents remain in their original location

