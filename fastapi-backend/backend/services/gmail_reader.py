import os.path
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from backend.services.llm_service import parse_email_content
import re
from backend.database.db import SessionLocal
from backend.database.models import Company, EmailLog
from sqlalchemy import or_

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                creds = None
                
        if not creds:
            secret_path = 'backend/client_secret_799220395615-dmkrtdvaeu2i7crtsk3otsig4uqgdft6.apps.googleusercontent.com.json'
            if not os.path.exists(secret_path):
                logger.error(f"{secret_path} file is missing! Please fetch it from the Google Cloud Console.")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
            # This will pop open a browser window for the user to grant access
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except HttpError as error:
        logger.error(f"An error occurred: {error}")
        return None

def read_latest_emails():
    """
    Fetch the last 5 emails that contain specific keywords.
    """
    service = get_gmail_service()
    if not service:
        return []

    db = SessionLocal()
    try:
        # Call the Gmail API - grab the latest 15 emails without keyword filtering 
        # so we don't miss regular conversational follow-ups.
        results = service.users().messages().list(
            userId='me', 
            maxResults=15
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return []
            
        parsed_emails = []
        for msg in messages:
            # We must fetch the individual message metadata by id
            txt = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From', 'Subject']).execute()
            
            headers = txt['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
            snippet = txt.get('snippet', '')
            
            # Analyze intent via LLM
            llm_insight = parse_email_content(snippet)
            
            parsed_emails.append({
                "sender": sender,
                "subject": subject,
                "snippet": snippet,
                "llm_insight": llm_insight
            })
            
            # Persist naturally
            match = re.search(r'<([^>]+)>', sender)
            external_hr_email = match.group(1).strip() if match else sender.strip()
            
            target_company = db.query(Company).filter(
                or_(
                    Company.email.ilike(external_hr_email),
                    Company.poc_email.ilike(external_hr_email),
                    Company.alternate_poc_email.ilike(external_hr_email)
                )
            ).first()
            if target_company:
                # Prevent pure duplicates blindly
                existing = db.query(EmailLog).filter(
                    EmailLog.company_id == target_company.id,
                    EmailLog.subject == subject,
                    EmailLog.body == snippet
                ).first()
                
                if not existing:
                    new_rec = EmailLog(
                        company_id=target_company.id,
                        direction="RECEIVED",
                        subject=subject,
                        body=snippet
                    )
                    db.add(new_rec)
                    db.commit()
            
        logger.info(f"Successfully retrieved {len(parsed_emails)} matching emails from Gmail.")
        return parsed_emails

    except HttpError as error:
        logger.error(f"An error occurred while fetching emails: {error}")
        return []
    finally:
        db.close()

# --- Quick Test Execution Block ---
if __name__ == "__main__":
    emails = read_latest_emails()
    print(f"Found {len(emails)} emails:")
    for i, email in enumerate(emails):
        print(f"\n{i+1}. From: {email['sender']}")
        print(f"   Subject: {email['subject']}")
        print(f"   Snippet: {email['snippet']}")
