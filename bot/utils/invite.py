"""
Telegram invite link creation and validation helpers.
"""

from datetime import datetime, timezone, timedelta
from aiogram import Bot


async def create_one_time_link(
    bot: Bot,
    channel_id: int,
    expiry_hours: int
) -> str:
    """Create member_limit=1 invite link. Returns the t.me URL."""
    link = await bot.create_chat_invite_link(
        chat_id=channel_id,
        member_limit=1,
        expire_date=datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
    )
    return link.invite_link


async def revoke_link(bot: Bot, channel_id: int, invite_link: str):
    """Revoke an invite link. Silently ignores if already expired."""
    try:
        await bot.revoke_chat_invite_link(channel_id, invite_link)
    except Exception:
        pass
