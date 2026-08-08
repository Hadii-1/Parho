# security.py
# -----------------------------------------------------------------------------
# Two security jobs live here:
#   1) Passwords  -> we NEVER store the real password. We store a "hash" of it.
#                    A hash is a scrambled, one-way version. Even we cannot turn
#                    it back into the password. We only check if a login password
#                    hashes to the same value.
#   2) JWT tokens -> after login we give the user a signed "token". The token
#                    proves who they are on later requests without sending the
#                    password every time.
# -----------------------------------------------------------------------------

from datetime import datetime, timedelta, timezone

import jwt  # from the PyJWT library
from passlib.context import CryptContext  # handles password hashing for us

from config import settings

# CryptContext picks the hashing algorithm. "bcrypt" is a well-known, safe one.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---- PASSWORDS --------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    """Turn a plain password into a safe-to-store hash (done at signup)."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a login attempt: does the typed password match the stored hash?
    Returns True if they match, False otherwise."""
    return pwd_context.verify(plain_password, hashed_password)


# ---- JWT TOKENS -------------------------------------------------------------
def create_access_token(user_id: str, email: str) -> str:
    """Build a signed token that says 'this is user X'. We put the user id and
    email inside, plus an expiry time, then sign it with our SECRET_KEY."""

    # "exp" is a standard field JWT understands: the moment the token expires.
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)

    # The "payload" is the data stored inside the token. "sub" (subject) is the
    # conventional place to put who the token belongs to.
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
    }

    # Sign and return the token as a string.
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Open a token and verify the signature + expiry. If anything is wrong
    (tampered, expired, fake) PyJWT raises an error, which the caller handles.
    On success it returns the payload dict we put in above."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
