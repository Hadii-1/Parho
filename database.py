# database.py
# -----------------------------------------------------------------------------
# This file connects to MongoDB and hands out "collections" (like tables).
# We keep the connection in one place so every other file shares the SAME
# connection instead of opening new ones over and over.
#
# MongoDB stores data as "documents" which look just like Python dictionaries.
# -----------------------------------------------------------------------------

from pymongo import MongoClient  # the official MongoDB driver for Python
from config import settings

# Create the client using the URI from config (default: local MongoDB).
# One MongoClient is meant to be reused for the whole app's lifetime.
#
# serverSelectionTimeoutMS=5000: if the database can't be reached, give up after
# 5 seconds instead of the default 30 (so we fail fast with a clear message).
# NOTE: creating the client does NOT connect yet — pymongo connects lazily, on
# the first real operation (like the create_index below).
client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)

# Pick the database (it is created automatically the first time we write to it).
db = client[settings.DB_NAME]

# "Collections" are like tables. We define the two we need:
users_collection = db["users"]      # one document per registered user
uploads_collection = db["uploads"]  # one document per uploaded PDF (for the daily limit)

# Create an index so looking up a user by their email is fast, and so the
# database itself refuses to store two users with the same email (unique=True).
# This is a safety net in addition to our own check in the signup code.
#
# We wrap this in try/except so a database that is unreachable AT STARTUP does not
# crash the whole app (which is what happened on Railway: with no MONGODB_URI set
# it fell back to localhost, which doesn't exist in the container, and the app
# died on boot). Now the app still starts, /health still works, and the log tells
# you exactly what to fix. Once the connection works, a restart recreates the index.
try:
    users_collection.create_index("email", unique=True)
except Exception as exc:
    # .rsplit("@", 1)[-1] shows only the host part of the URI (everything AFTER the
    # last "@"), never the username/password — safe to print in logs.
    target = settings.MONGODB_URI.rsplit("@", 1)[-1]
    print("[Parho] WARNING: could not reach MongoDB at startup.")
    print(f"[Parho]   reason: {exc}")
    print(f"[Parho]   tried to connect to: {target}")
    print("[Parho]   -> If this is a cloud deploy (e.g. Railway), set MONGODB_URI in your")
    print("[Parho]      service's Variables to your MongoDB Atlas connection string, and")
    print("[Parho]      make sure Atlas Network Access allows 0.0.0.0/0. Then redeploy.")
