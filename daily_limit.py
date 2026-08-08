# daily_limit.py
# -----------------------------------------------------------------------------
# This file enforces the rule: each user may upload only 2 PDFs per day.
#
# How it works:
#   Every time a PDF is accepted we write a small record into the "uploads"
#   collection with the user's id and today's date (as text like "2026-08-08").
#   To check the limit we simply COUNT how many records that user already has
#   for today. If the count is >= the max, we block the upload.
#
# Using the date as plain text (YYYY-MM-DD) makes "same day" easy to compare
# and the limit naturally resets at midnight, because a new day is a new string.
# -----------------------------------------------------------------------------

from datetime import datetime, timezone

from database import uploads_collection
from config import settings


def _today_str() -> str:
    """Return today's date as text, e.g. '2026-08-08'. We use UTC so the reset
    time is consistent no matter where the user is."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def count_today(user_id: str) -> int:
    """How many PDFs has this user already uploaded today?"""
    return uploads_collection.count_documents({
        "user_id": user_id,
        "date": _today_str(),
    })


def can_upload(user_id: str) -> bool:
    """True if the user is still under the daily limit (has room for one more)."""
    return count_today(user_id) < settings.MAX_PDFS_PER_DAY


def remaining_today(user_id: str) -> int:
    """How many uploads the user has left today (never negative). Handy for
    showing "1 upload left" in the UI."""
    left = settings.MAX_PDFS_PER_DAY - count_today(user_id)
    return max(left, 0)


def record_upload(user_id: str, filename: str) -> None:
    """Save a record that this user uploaded a PDF today. Call this ONLY after
    an upload succeeds, so failed uploads don't burn a user's daily quota."""
    uploads_collection.insert_one({
        "user_id": user_id,
        "filename": filename,
        "date": _today_str(),
        "created_at": datetime.now(timezone.utc),
    })
