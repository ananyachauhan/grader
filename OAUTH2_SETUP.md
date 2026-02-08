# OAuth2 Authentication Setup Guide

This guide explains how to set up OAuth2 authentication so users can access their Google Drive files (including shared folders) using their own Google accounts.

## Why OAuth2?

- **Personal API keys** can only access publicly shared files
- **OAuth2** allows users to authenticate with their own Google accounts
- Users can access **any Drive folder shared with their account** (including school shared drives)
- Each user (teacher, TA) authenticates once, then the token is saved for future use

## Setup Steps

### 1. Create OAuth2 Credentials (One-time setup)

**Use your personal Google account** (since school account may be blocked):

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your **personal Google account**
3. Select or create a project
4. Enable APIs:
   - Go to "APIs & Services" → "Library"
   - Enable: **Google Drive API** and **Google Docs API**
5. Configure OAuth Consent Screen:
   - Go to "APIs & Services" → "OAuth consent screen"
   - User Type: **External**
   - App name: "Grading System" (or any name)
   - User support email: your personal email
   - Developer contact: your personal email
   - Add scopes:
     - `https://www.googleapis.com/auth/drive.readonly`
     - `https://www.googleapis.com/auth/documents.readonly`
     - `https://www.googleapis.com/auth/documents`
   - Save and continue through all steps
6. Create OAuth Client ID:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: **Web application**
   - Name: "Grading System Web Client"
   - Authorized redirect URIs:
     ```
     http://localhost:5000/api/documents/auth/callback
     ```
     (If deploying to a server, also add: `https://your-server.com/api/documents/auth/callback`)
   - Click "Create"
7. Download credentials:
   - Click the download icon (⬇) next to your OAuth 2.0 Client ID
   - Save the JSON file as `client_secrets.json` in your project root (`C:\Users\anany\grader\`)

### 2. Update Environment Variables

Add to your `.env` file (optional, defaults to `client_secrets.json`):

```env
GOOGLE_CLIENT_SECRETS_FILE=client_secrets.json
FLASK_SECRET_KEY=your-random-secret-key-here
```

### 3. Start the Application

```bash
python app.py
```

## How Users Authenticate

### First Time (Each User)

1. User visits the grading page
2. Sees "Not authenticated" status
3. Clicks "Authenticate with Google" button
4. Opens Google sign-in page in a popup window
5. **User signs in with their school Google account** (the one that has access to the shared Drive folder)
6. Grants permissions
7. Popup closes automatically
8. Status updates to "✓ Authenticated"
9. Token is saved in `token.json` for future use

### Subsequent Uses

- Token is automatically loaded from `token.json`
- If token expires, it's automatically refreshed
- No need to authenticate again

## How It Works

1. **OAuth2 credentials** (from your personal Google Cloud account) are used to initiate the authentication flow
2. **Users authenticate** with their own Google accounts (school accounts)
3. **Token is saved** locally in `token.json`
4. **All API calls** use the user's token to access their Drive files
5. **Shared folders** are accessible because the user's account has access to them

## File Structure

```
grader/
├── client_secrets.json    # OAuth2 credentials (from Google Cloud Console)
├── token.json             # User's authentication token (auto-generated)
├── .env                   # Environment variables
└── ...
```

## Security Notes

- `client_secrets.json` and `token.json` are in `.gitignore` (not committed to git)
- Each user has their own `token.json` (if running locally)
- Tokens are stored locally on the server/computer
- Tokens can be revoked by users in their Google account settings

## Troubleshooting

### "OAuth2 client secrets file not found"
- Make sure `client_secrets.json` is in the project root
- Check the file name matches `GOOGLE_CLIENT_SECRETS_FILE` in `.env`

### "Authentication required" error
- User needs to authenticate by clicking "Authenticate with Google"
- Make sure the redirect URI in Google Cloud Console matches your server URL

### "Access denied" when loading documents
- User needs to sign in with the Google account that has access to the Drive folder
- Make sure the folder is shared with the user's account

### Token expires
- Tokens are automatically refreshed if a refresh token exists
- If refresh fails, user needs to authenticate again

## Multi-User Setup

If multiple users (teacher, TAs) will use the system:

- **Each user authenticates once** with their own school account
- **Each user's token** is saved separately
- **All users can access** folders shared with their accounts

For a shared server:
- Consider using a database to store tokens per user
- Or use service account if all users share the same Drive access

## Next Steps

After setting up OAuth2:
1. Test authentication by visiting the grading page
2. Authenticate with your school account
3. Try loading documents from a shared Drive folder
4. Verify you can access the files

