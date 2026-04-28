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
from backend.database.models import Company, EmailLog, StudentQuestion, TelegramGroup
import base64
from sqlalchemy import or_
import io
import PyPDF2
def extract_body(payload):
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data', '')
                if data:
                    data += "=" * ((4 - len(data) % 4) % 4)
                    body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif 'parts' in part:
                body += extract_body(part)
    elif payload['mimeType'] == 'text/plain':
        data = payload['body'].get('data', '')
        if data:
            data += "=" * ((4 - len(data) % 4) % 4)
            body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    return body

def extract_pdf_attachments(service, msg_id, payload):
    pdf_texts = []
    
    def walk_parts(parts):
        for part in parts:
            filename = part.get('filename')
            if filename and filename.lower().endswith('.pdf'):
                att_id = part['body'].get('attachmentId')
                if att_id:
                    try:
                        att = service.users().messages().attachments().get(
                            userId='me', messageId=msg_id, id=att_id
                        ).execute()
                        data = base64.urlsafe_b64decode(att['data'])
                        reader = PyPDF2.PdfReader(io.BytesIO(data))
                        text = f"\n\n[Attachment: {filename}]\n"
                        for page in reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                        pdf_texts.append(text)
                    except Exception as e:
                        logger.error(f"Failed to parse PDF attachment {filename}: {e}")
            elif 'parts' in part:
                walk_parts(part['parts'])
                
    if 'parts' in payload:
        walk_parts(payload['parts'])
        
    return "".join(pdf_texts)

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

def read_latest_emails(db=None, force_company_id=None):
    """
    Fetch the last 5 emails that contain specific keywords.
    """
    service = get_gmail_service()
    if not service:
        return []

    session = db or SessionLocal()
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
            txt = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            
            headers = txt['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
            snippet = txt.get('snippet', '')
            
            full_body = extract_body(txt['payload'])
            if not full_body.strip():
                full_body = snippet
                
            pdf_text = extract_pdf_attachments(service, msg['id'], txt['payload'])
            if pdf_text:
                full_body += pdf_text
            
            # Check if this email belongs to a target company
            match = re.search(r'<([^>]+)>', sender)
            external_hr_email = match.group(1).strip() if match else sender.strip()
            
            target_company = session.query(Company).filter(
                or_(
                    Company.email.ilike(f"%{external_hr_email}%"),
                    Company.poc_email.ilike(f"%{external_hr_email}%"),
                    Company.alternate_poc_email.ilike(f"%{external_hr_email}%")
                )
            ).first()
            
            if target_company:
                # Prevent pure duplicates blindly
                existing = session.query(EmailLog).filter(
                    EmailLog.company_id == target_company.id,
                    EmailLog.subject == subject,
                    or_(EmailLog.body == snippet, EmailLog.body == full_body)
                ).first()
                
                if existing:
                    if existing.body == snippet and full_body != snippet and len(full_body) > len(snippet):
                        existing.body = full_body
                        session.commit()
                
                if not existing:
                    # Analyze intent via LLM only for new, matched emails
                    llm_insight = parse_email_content(snippet)
                    
                    new_rec = EmailLog(
                        company_id=target_company.id,
                        direction="RECEIVED",
                        subject=subject,
                        body=full_body
                    )
                    session.add(new_rec)
                    session.commit()
                    
                    # NEW LOGIC: Check for FORWARDED_TO_HR questions
                    forwarded_qs = session.query(StudentQuestion).filter(
                        StudentQuestion.company_id == target_company.id,
                        StudentQuestion.status == "FORWARDED_TO_HR"
                    ).all()
                    
                    if forwarded_qs:
                        from backend.services.llm_service import extract_answers_from_hr_email
                        from backend.services.company_agent import _send_bot_message
                        
                        # Use LLM to see if this new email answers the questions
                        answers_dict = extract_answers_from_hr_email(full_body, [q.question_text for q in forwarded_qs])
                        
                        if answers_dict:
                            tg_group = session.query(TelegramGroup).filter(TelegramGroup.company_id == target_company.id, TelegramGroup.is_active == True).first()
                            
                            for q in forwarded_qs:
                                ans = answers_dict.get(q.question_text)
                                if ans:
                                    q.hr_answer = ans
                                    q.status = "HR_ANSWERED"
                                    
                                    if tg_group:
                                        reply_text = f"@{q.telegram_user} Update regarding your query ('{q.question_text[:30]}...'):\n\nHR Says: {ans}"
                                        _send_bot_message(tg_group.chat_id, reply_text)
                            
                            session.commit()
                    
            parsed_emails.append({
                "sender": sender,
                "subject": subject,
                "snippet": snippet,
                "llm_insight": llm_insight if 'llm_insight' in locals() else {"intent": "UNKNOWN", "time": None}
            })

            
        logger.info(f"Successfully retrieved {len(parsed_emails)} matching emails from Gmail.")
        return parsed_emails

    except HttpError as error:
        logger.error(f"An error occurred while fetching emails: {error}")
        return []
    finally:
        if db is None:
            session.close()

import threading
import time

def _gmail_sync_loop():
    logger.info("Started background Gmail sync thread.")
    while True:
        try:
            read_latest_emails()
        except Exception as e:
            logger.error(f"Error in background Gmail sync: {e}")
        # Poll every 20 seconds for near real-time notifications without hitting rate limits too fast
        time.sleep(20)

def start_gmail_sync_thread():
    thread = threading.Thread(target=_gmail_sync_loop, daemon=True)
    thread.start()
# --- Quick Test Execution Block ---
if __name__ == "__main__":
    emails = read_latest_emails()
    print(f"Found {len(emails)} emails:")
    for i, email in enumerate(emails):
        print(f"\n{i+1}. From: {email['sender']}")
        print(f"   Subject: {email['subject']}")
        print(f"   Snippet: {email['snippet']}")
