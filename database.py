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
client = MongoClient(settings.MONGODB_URI)

# Pick the database (it is created automatically the first time we write to it).
db = client[settings.DB_NAME]

# "Collections" are like tables. We define the two we need:
users_collection = db["users"]      # one document per registered user
uploads_collection = db["uploads"]  # one document per uploaded PDF (for the daily limit)

# Create an index so looking up a user by their email is fast, and so the
# database itself refuses to store two users with the same email (unique=True).
# This is a safety net in addition to our own check in the signup code.
users_collection.create_index("email", unique=True)
