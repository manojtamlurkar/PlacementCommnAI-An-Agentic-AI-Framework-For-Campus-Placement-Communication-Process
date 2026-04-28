import os
import time
import logging
import threading
import requests
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database.db import SessionLocal
from backend.database.models import TelegramGroup, StudentQuestion, Company, EmailLog, RecruitmentDrive
from backend.services.llm_service import answer_student_question, draft_questions_to_hr
from backend.services.telegram_group_service import post_to_company_group
from backend.services.email_service import send_email

logger = logging.getLogger(__name__)

def poll_telegram_updates():
    """
    Background worker that continuously polls Telegram for new messages.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("No TELEGRAM_BOT_TOKEN found. Company Agent polling disabled.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    offset = None
    
    logger.info("Company Agent Telegram polling started...")
    
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset
                
            response = requests.get(url, params=params, timeout=40)
            if not response.ok:
                time.sleep(5)
                continue
                
            data = response.json()
            if not data.get("ok"):
                time.sleep(5)
                continue
                
            updates = data.get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                
                if "message" in update:
                    process_message(update["message"])
                    
        except Exception as e:
            logger.error(f"Telegram polling error: {e}")
            time.sleep(5)

def _send_bot_message(chat_id: str, text: str):
    """
    Sends a message to a Telegram chat directly via HTTP (synchronous).
    Used inside the polling thread where asyncio loop is already running.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        resp = requests.post(url, json=payload, timeout=10)
        if not resp.ok:
            logger.error(f"Bot reply failed: {resp.text}")
        else:
            logger.info(f"Bot replied to chat {chat_id}")
    except Exception as e:
        logger.error(f"Bot reply exception: {e}")


def process_message(message: dict):
    """
    Process an incoming Telegram message.
    """
    chat = message.get("chat", {})
    chat_id = str(chat.get("id"))
    text = message.get("text", "").strip()
    msg_id = message.get("message_id")
    
    # We only care about text messages in groups/supergroups
    if chat.get("type") not in ("supergroup", "group") or not text:
        return
        
    from_user = message.get("from", {})
    user_name = from_user.get("first_name", "")
    if from_user.get("last_name"):
        user_name += f" {from_user['last_name']}"
    user_id = str(from_user.get("id", ""))
    
    # Don't process our own bot's messages
    if from_user.get("is_bot"):
        return
        
    # Check if this message is a command (we can ignore or process them later)
    if text.startswith("/"):
        return

    db = SessionLocal()
    try:
        # Check if this chat is a registered company group
        tg_group = db.query(TelegramGroup).filter(TelegramGroup.chat_id == chat_id).first()
        if not tg_group:
            return # Ignore messages from other groups

        company = db.query(Company).filter(Company.id == tg_group.company_id).first()
        if not company:
            return
            
        logger.info(f"Received question from {user_name} in {company.company_name} group: {text}")

        from backend.services.gmail_reader import read_latest_emails
        try:
            read_latest_emails(db, force_company_id=company.id)
        except Exception as e:
            logger.error(f"Failed to sync emails before answering question: {e}")

        # Gather context (Knowledge Base rows instead of raw emails)
        from backend.database.models import KnowledgeBaseEntry
        kb_entries = db.query(KnowledgeBaseEntry).filter(
            KnowledgeBaseEntry.company_id == company.id
        ).all()
        
        if kb_entries:
            company_kb = "\n".join([f"- [{e.category}] {e.topic}: {e.content}" for e in kb_entries])
        else:
            company_kb = ""
        
        # Call LLM
        ans_data = answer_student_question(text, company.company_name, company_kb)
        
        can_answer = ans_data.get("can_answer", False)
        auto_answer_text = ans_data.get("answer", "")
        
        drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.id == tg_group.drive_id).first()
        spoc_name = drive.spoc_name if (drive and drive.spoc_name) else "CDC NITK Surathkal"

        if can_answer and auto_answer_text:
            new_q_status = "AUTO_ANSWERED"
            reply_text = f"@{from_user.get('username', user_name)} {auto_answer_text}"
        else:
            new_q_status = "FORWARDED_TO_HR"
            # Auto-forward to HR
            draft = draft_questions_to_hr(
                questions_list=[text],
                company_name=company.company_name,
                poc_name=company.poc_name,
                spoc_name=spoc_name
            )
            subject = f"Student Query - {company.company_name} Campus Drive"
            send_email(company.email, subject, draft, company.id, db)
            
            reply_text = f"@{from_user.get('username', user_name)} I don't have the details for that yet. I've automatically emailed the HR to ask. I'll let you know as soon as they reply!"
        
        # Save question to DB
        new_q = StudentQuestion(
            company_id=company.id,
            drive_id=tg_group.drive_id,
            telegram_user=user_name,
            telegram_user_id=user_id,
            question_text=text,
            message_id=str(msg_id),
            status=new_q_status,
            auto_answer=auto_answer_text if can_answer else None,
            answered_at=datetime.utcnow() if can_answer else None
        )
        db.add(new_q)
        db.commit()

        # Use requests directly (synchronous) — cannot call run_until_complete from a running thread
        _send_bot_message(chat_id, reply_text)

    except Exception as e:
        logger.error(f"Error processing message: {e}")
    finally:
        db.close()

def start_agent_thread():
    """Starts the polling thread."""
    thread = threading.Thread(target=poll_telegram_updates, daemon=True)
    thread.start()
