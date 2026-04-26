import os
import time
import logging
import threading
import requests
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database.db import SessionLocal
from backend.database.models import TelegramGroup, StudentQuestion, Company, EmailLog
from backend.services.llm_service import answer_student_question
from backend.services.telegram_group_service import post_to_company_group

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

def process_message(message: dict):
    """
    Process an incoming Telegram message.
    """
    chat = message.get("chat", {})
    chat_id = str(chat.get("id"))
    text = message.get("text", "").strip()
    msg_id = message.get("message_id")
    
    # We only care about text messages in supergroups
    if chat.get("type") != "supergroup" or not text:
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

        # Gather context
        history = db.query(EmailLog).filter(EmailLog.company_id == company.id).order_by(EmailLog.timestamp.asc()).all()
        email_history = [{"direction": e.direction, "subject": e.subject, "body": e.body} for e in history]
        
        # Call LLM
        ans_data = answer_student_question(text, company.company_name, company.description, email_history)
        
        can_answer = ans_data.get("can_answer", False)
        auto_answer_text = ans_data.get("answer", "")
        
        # Save question to DB
        new_q = StudentQuestion(
            company_id=company.id,
            drive_id=tg_group.drive_id,
            telegram_user=user_name,
            telegram_user_id=user_id,
            question_text=text,
            message_id=str(msg_id),
            status="AUTO_ANSWERED" if can_answer else "ESCALATED",
            auto_answer=auto_answer_text if can_answer else None,
            answered_at=datetime.utcnow() if can_answer else None
        )
        db.add(new_q)
        db.commit()

        # Send response back to group if applicable
        if can_answer and auto_answer_text:
            reply_text = f"@{from_user.get('username', user_name)} {auto_answer_text}"
            post_to_company_group(chat_id, reply_text)
        else:
            # We don't necessarily need to tell them we escalated it unless we want to, 
            # maybe just a brief acknowledgment.
            reply_text = f"@{from_user.get('username', user_name)} I don't have the details for that yet. I've escalated your question to the CDC SPOC to check with HR."
            post_to_company_group(chat_id, reply_text)

    except Exception as e:
        logger.error(f"Error processing message: {e}")
    finally:
        db.close()

def start_agent_thread():
    """Starts the polling thread."""
    thread = threading.Thread(target=poll_telegram_updates, daemon=True)
    thread.start()
