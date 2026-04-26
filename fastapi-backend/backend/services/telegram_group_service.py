"""
Telegram Group Service (Phase 2)
---------------------------------
Uses Telethon (MTProto) to:
1. Create a named supergroup for a company's drive
2. Add the CDC bot as admin
3. Export an invite link
4. Broadcast the invite to the main student channel

Session file (telegram_session.session) must exist — run setup_telegram_session.py first.
"""
import os
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

API_ID       = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH     = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
MAIN_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SESSION_FILE = "telegram_session"

# Extract the bot username from token for adding it to groups
# Format: <bot_id>:AAH...  — we'll look it up dynamically instead
BOT_USERNAME_CACHE = {}


def _get_event_loop():
    """Get or create an event loop safely (Python 3.8 compatible)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


async def _create_group_async(group_name: str) -> dict:
    """
    Core async function:
    1. Create supergroup
    2. Resolve bot username
    3. Add bot as admin
    4. Export invite link
    """
    from telethon import TelegramClient
    from telethon.tl.functions.channels import (
        CreateChannelRequest,
        InviteToChannelRequest,
        EditAdminRequest,
    )
    from telethon.tl.functions.messages import ExportChatInviteRequest
    from telethon.tl.types import ChatAdminRights
    from telethon.errors import SessionPasswordNeededError

    session_path = SESSION_FILE
    if not os.path.exists(f"{session_path}.session"):
        raise FileNotFoundError(
            "telegram_session.session not found. "
            "Please run setup_telegram_session.py first to authenticate."
        )

    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        # 1. Create the supergroup
        result = await client(CreateChannelRequest(
            title=group_name,
            about=f"Official coordination group for {group_name}. Managed by CDC NITK Surathkal.",
            megagroup=True,   # True = supergroup (not broadcast channel)
        ))
        channel = result.chats[0]
        chat_id = str(-100_000_000_000 - channel.id)  # Standard Telegram supergroup ID format

        logger.info(f"Created Telegram supergroup: {group_name} (chat_id={chat_id})")

        # 2. Resolve the bot entity by its token prefix (bot_id)
        bot_id = int(BOT_TOKEN.split(":")[0])
        try:
            bot_entity = await client.get_entity(bot_id)
            # 3. Invite bot to group
            await client(InviteToChannelRequest(channel=channel, users=[bot_entity]))
            logger.info(f"Added bot {bot_entity.username} to group {group_name}")

            # 4. Promote bot to admin with full rights
            admin_rights = ChatAdminRights(
                post_messages=True,
                edit_messages=True,
                delete_messages=True,
                ban_users=True,
                invite_users=True,
                pin_messages=True,
                add_admins=False,
                manage_call=False,
                change_info=False,
            )
            await client(EditAdminRequest(
                channel=channel,
                user_id=bot_entity,
                admin_rights=admin_rights,
                rank="CDC Bot"
            ))
            logger.info(f"Promoted bot to admin in {group_name}")
        except Exception as e:
            logger.warning(f"Could not add/promote bot: {e} — group still created.")

        # 5. Export permanent invite link
        invite = await client(ExportChatInviteRequest(peer=channel))
        invite_link = invite.link if hasattr(invite, 'link') else None
        logger.info(f"Invite link: {invite_link}")

        return {
            "chat_id": chat_id,
            "group_name": group_name,
            "invite_link": invite_link,
        }


async def _broadcast_invite_async(invite_link: str, company_name: str, message: str = None):
    """Post the invite link to the main student Telegram channel."""
    import requests
    text = message or (
        f"📢 *New Company Drive Group Created!*\n\n"
        f"Company: *{company_name}*\n"
        f"Join the dedicated group for updates, Q&A, and logistics:\n"
        f"👉 {invite_link}\n\n"
        f"_Posted by CDC NITK Surathkal Recruitment System_"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": MAIN_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }
    resp = requests.post(url, json=payload, timeout=10)
    if not resp.ok:
        logger.error(f"Failed to broadcast invite: {resp.text}")
        return False
    logger.info(f"Invite link broadcasted to main channel for {company_name}")
    return True


async def _post_to_group_async(chat_id: str, message: str):
    """Post a message to a specific company Telegram group via the bot."""
    import requests
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }
    resp = requests.post(url, json=payload, timeout=10)
    if not resp.ok:
        logger.error(f"Failed to post to group {chat_id}: {resp.text}")
        return False
    return True


# ---------------------------------------------------------------------------
# Public synchronous API (called from FastAPI routes)
# ---------------------------------------------------------------------------

def create_company_telegram_group(company_name: str, drive_date: str = None) -> dict:
    """
    Creates a dedicated Telegram supergroup for a company's drive.
    Returns: {chat_id, group_name, invite_link}
    Raises: FileNotFoundError if session not set up yet.
    """
    suffix = f" — {drive_date}" if drive_date else " — NITK Drive 2026"
    group_name = f"{company_name}{suffix}"

    loop = _get_event_loop()
    result = loop.run_until_complete(_create_group_async(group_name))
    return result


def broadcast_invite_to_main_channel(invite_link: str, company_name: str, custom_message: str = None) -> bool:
    """Broadcasts the group invite link to the main student Telegram channel."""
    loop = _get_event_loop()
    return loop.run_until_complete(_broadcast_invite_async(invite_link, company_name, custom_message))


def post_to_company_group(chat_id: str, message: str) -> bool:
    """Posts a message to a specific company's dedicated Telegram group."""
    loop = _get_event_loop()
    return loop.run_until_complete(_post_to_group_async(chat_id, message))
