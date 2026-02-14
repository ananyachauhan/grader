# MaroonGrader

MaroonGrader is an AI-powered grading platform designed for instructors and teaching assistants to automate the evaluation of writing assignments. It uses Google Gemini AI to analyze student submissions, generate personalized feedback, and apply rubric-based scoring—significantly reducing the time spent on manual grading while maintaining academic quality and consistency.

The platform integrates directly with Google Drive and Google Docs, allowing instructors to load student submissions, grade them with AI assistance, review and edit the feedback, and then automatically insert the finalized feedback and rubric scores into the documents. All AI-generated content is highlighted in the documents so students can clearly see what the instructor has added.

## Key Features

**AI-Powered Grading**: Uses Google Gemini LLMs to evaluate writing assignments based on custom rubrics and grading instructions. The system supports multiple Gemini models with automatic fallback for reliability.

**Human Review Workflow**: AI grading results are stored for review before being added to documents. Instructors can review, edit, and approve feedback and scores through a dedicated review dashboard. Documents are only updated in Google Docs after approval.

**Section-Based Organization**: Organizes assignments by course sections (e.g., 900, 901, 902), making it easy to manage multiple classes and track assignments per section.

**Rubric Management**: Supports custom rubrics in JSON format or Word documents. Rubrics can be parsed automatically from Word/PDF files using AI, or created manually.

**Batch Processing**: Grade multiple documents at once with progress tracking. The system handles errors gracefully, allowing partial success when some documents fail.

**Performance Analytics**: Generates class-wide performance summaries including average scores, grade distributions, and AI-generated insights about common strengths and issues across all submissions.

**Document Management**: Automatically converts Word documents to Google Docs format, tracks document status (ungraded, pending review, reviewed), and renames documents upon completion.

## Technology Stack

- **Backend**: Flask (Python) with SQLAlchemy ORM
- **Database**: SQLite (with pysqlite3 for Fly.io deployment)
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **AI**: Google Gemini API (via google-generativeai SDK)
- **APIs**: Google Drive API, Google Docs API (OAuth2 authentication)
- **Deployment**: Fly.io with Gunicorn

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Google Cloud account with Drive and Docs APIs enabled
- Google AI Studio account for Gemini API key

### Installation

1. Clone the repository and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables in a `.env` file:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   GOOGLE_CREDENTIALS_PATH=path/to/service-account-key.json
   ```

3. Initialize the database (runs automatically on first start):
   ```bash
   python app.py
   ```

4. Access the application at `http://localhost:5000`

### First Steps

1. **Create an Assignment**: Navigate to a section, create a new assignment, and configure the rubric and Google Drive folder.

2. **Grade Documents**: Load documents from the Drive folder, select which ones to grade, and run the grading process. Results are saved for review.

3. **Review Feedback**: Use the Review dashboard to examine AI-generated feedback, edit as needed, and approve to sync to Google Docs.

4. **View Analytics**: Check assignment summaries to see class-wide performance metrics and insights.

## Configuration

The system uses a configuration file (`config/config.json`) for default settings including AI model selection, grading parameters, and document formatting options. Rubrics are stored in the `rubrics/` directory and can be uploaded through the web interface.

## Deployment

The application is configured for deployment on Fly.io with persistent storage for the SQLite database and rubric files. Set secrets using `fly secrets set` for API keys and credentials.

## License

This project is provided as-is for educational use.
