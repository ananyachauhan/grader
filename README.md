# AI Grading Automation System

An automated grading system that uses Google Gemini AI to grade student assignments in Google Docs, insert comments, and add rubric tables. Built with n8n workflows and Python scripts.

## Features

- 🤖 **AI-Powered Grading**: Uses Google Gemini API (free tier) to evaluate assignments
- 📝 **Automatic Comment Insertion**: Adds constructive feedback directly in Google Docs
- 📊 **Rubric Table Generation**: Inserts formatted rubric tables with scores
- 🔄 **Batch Processing**: Grade multiple documents automatically
- 🆓 **100% Free**: Uses free tier APIs (Gemini, Google Drive/Docs)
- 🔧 **Flexible Rubrics**: Easy-to-create JSON rubric templates

## Architecture

```
Google Drive Folder
    ↓
n8n Workflow:
    1. List Google Docs
    2. For each document:
       a. Extract text
       b. Grade with AI (Gemini)
       c. Insert comments
       d. Insert rubric table
    3. Move to "Graded" folder
```

## Prerequisites

- Python 3.8 or higher
- n8n (self-hosted or cloud)
- Google Cloud account
- Google AI Studio account (for Gemini API)

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Google Cloud APIs

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable the following APIs:
   - Google Drive API
   - Google Docs API
4. Create credentials:
   - **Option A**: OAuth2 Client ID (for user authentication)
   - **Option B**: Service Account (for automated access)
     - Create service account
     - Download JSON key file
     - Share your Google Drive folders with the service account email

### 3. Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the API key

### 4. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp config/.env.example config/.env
   ```

2. Edit `config/.env` and add your credentials:
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id_here
   GRADED_FOLDER_ID=your_graded_folder_id_here
   GOOGLE_CREDENTIALS_PATH=path/to/service-account-key.json
   ```

### 5. Get Google Drive Folder IDs

1. Open your Google Drive folder in a browser
2. The folder ID is in the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
3. Copy the folder ID and add it to `.env`

### 6. Set Up n8n

#### Option A: Self-Hosted n8n

1. Install n8n:
   ```bash
   npm install n8n -g
   # or
   npx n8n
   ```

2. Import the workflow:
   - Open n8n UI (usually http://localhost:5678)
   - Go to Workflows → Import
   - Select `workflows/grading_workflow.json`

3. Configure credentials:
   - Set up Google Drive OAuth2 credentials in n8n
   - Add environment variables in n8n settings

#### Option B: n8n Cloud

1. Sign up at [n8n.io](https://n8n.io)
2. Import the workflow JSON
3. Configure credentials and environment variables

### 7. Customize Rubrics

1. Edit existing rubrics in `rubrics/` folder
2. Create new rubrics following the JSON structure:
   ```json
   {
     "name": "Your Rubric Name",
     "total_points": 100,
     "criteria": [
       {
         "name": "Criterion Name",
         "max_points": 20,
         "description": "Description of what to evaluate"
       }
     ]
   }
   ```

3. Update `config/config.json` to set default rubric

## Usage

### Method 1: Using n8n Workflow (Recommended)

1. Ensure your Google Drive folder contains student submissions
2. Open n8n workflow
3. Click "Execute Workflow" (manual trigger)
4. The workflow will:
   - List all Google Docs in the folder
   - Grade each document automatically
   - Insert comments and rubric tables
   - Move graded documents to the "Graded" folder

### Method 2: Command Line (Testing)

Test individual components:

```bash
# Extract text from a document
python scripts/extract_text.py DOCUMENT_ID

# Grade a document (requires text file and rubric)
python scripts/ai_grader.py document.txt rubrics/memo_rubric.json

# Insert comments
python scripts/insert_comments.py DOCUMENT_ID comments.json

# Insert rubric table
python scripts/insert_rubric.py DOCUMENT_ID rubrics/memo_rubric.json scores.json

# Full workflow
python scripts/grading_workflow.py DOCUMENT_ID [rubric_path]
```

### Method 3: Python Script Directly

```python
from scripts.grading_workflow import grade_document

result = grade_document(
    doc_id="YOUR_DOCUMENT_ID",
    rubric_path="rubrics/memo_rubric.json"
)

print(result)
```

## Configuration

### config/config.json

- `default_rubric`: Default rubric file to use
- `ai_model`: Gemini model settings
- `grading`: Comment style and preferences
- `document`: Document formatting options

### Environment Variables

- `GOOGLE_API_KEY`: Google Cloud API key
- `GEMINI_API_KEY`: Google Gemini API key
- `GOOGLE_DRIVE_FOLDER_ID`: Folder containing submissions
- `GRADED_FOLDER_ID`: Folder for completed gradings
- `GOOGLE_CREDENTIALS_PATH`: Path to service account JSON (optional)

## Free Tier Limits

### Google Gemini API
- 15 requests per minute
- 1,500 requests per day
- Approximately 50-100 documents per day (depending on document size)

### Google Drive/Docs API
- 1,000 requests per 100 seconds per user
- Usually sufficient for grading workflows

## Troubleshooting

### "GOOGLE_API_KEY not set" Error
- Make sure `.env` file exists in `config/` folder
- Check that environment variables are loaded correctly

### "Document appears to be empty"
- Verify the document ID is correct
- Check that the service account has access to the document
- Ensure the document is a Google Doc (not PDF or Word)

### "GEMINI_API_KEY not set"
- Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- Add to `.env` file

### Comments Not Inserting
- Check that credentials have write access to documents
- Verify document permissions
- Check n8n logs for specific error messages

### n8n Workflow Not Executing
- Verify Python path is correct in n8n settings
- Check that all environment variables are set in n8n
- Ensure Google Drive credentials are configured

## Project Structure

```
grader/
├── scripts/
│   ├── extract_text.py          # Extract text from Google Docs
│   ├── ai_grader.py              # AI grading with Gemini
│   ├── insert_comments.py        # Insert comments into Docs
│   ├── insert_rubric.py          # Insert rubric tables
│   └── grading_workflow.py       # Main orchestrator
├── workflows/
│   └── grading_workflow.json     # n8n workflow definition
├── config/
│   ├── .env.example              # Environment variable template
│   └── config.json               # Runtime configuration
├── rubrics/
│   └── memo_rubric.json          # Example rubric template
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Extending the System

### Adding New Rubric Types

1. Create new JSON file in `rubrics/` folder
2. Follow the same structure as `memo_rubric.json`
3. Update `config/config.json` to set as default (optional)

### Customizing AI Prompts

Edit `scripts/ai_grader.py` → `create_grading_prompt()` function to customize how the AI evaluates assignments.

### Adding Canvas Integration

The system is designed to work with Google Drive. To add Canvas:
1. Use Canvas API to download submissions
2. Upload to Google Drive (or convert to Google Docs)
3. Run existing workflow

## Security Notes

- Never commit `.env` files or credentials to version control
- Use service accounts with minimal required permissions
- Regularly rotate API keys
- Review AI-generated feedback before sharing with students

## License

This project is provided as-is for educational use.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review n8n and Google API documentation
3. Check error logs in n8n workflow execution

## Future Enhancements

- [ ] Canvas LMS direct integration
- [ ] Web UI for rubric management
- [ ] Review/edit step before auto-insertion
- [ ] Support for multiple file formats
- [ ] Email notifications to students
- [ ] Grading analytics dashboard
