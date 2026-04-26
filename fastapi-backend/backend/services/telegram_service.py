import os
import requests
import logging
from backend.services.llm_service import generate_telegram_message

logger = logging.getLogger(__name__)

def send_telegram_message(company_name: str) -> bool:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logger.error("Telegram credentials missing in environment. Ensure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    message = generate_telegram_message(company_name)
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    
    try:
        response = requests.post(url, json=payload)
        
        # This will print the EXACT reason Telegram rejected the message (e.g. "chat not found")
        if not response.ok:
            logger.error(f"Telegram API Error Details: {response.text}")
            
        response.raise_for_status()
        logger.info("Telegram message sent successfully.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

def send_telegram_draft(message: str) -> bool:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logger.error("Telegram credentials missing in environment. Ensure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    
    try:
        response = requests.post(url, json=payload)
        
        if not response.ok:
            logger.error(f"Telegram API Error Details: {response.text}")
            
        response.raise_for_status()
        logger.info("Telegram message sent successfully.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False
