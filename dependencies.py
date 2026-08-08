# dependencies.py
# -----------------------------------------------------------------------------
# A "dependency" in FastAPI is a function that runs BEFORE your route function.
# Here we build get_current_user: it reads the login token from the request,
# checks it, and returns the matching user. Any route that adds this dependency
# becomes "protected" -- it only runs for logged-in users.
# -----------------------------------------------------------------------------

from bson import ObjectId  # MongoDB stores ids as ObjectId, not plain strings
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database import users_collection
from security import decode_access_token

# HTTPBearer tells FastAPI to look for a header like:  Authorization: Bearer <token>
# It also makes the little "Authorize" button appear in the auto docs at /docs.
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Return the logged-in user's document, or raise 401 (Unauthorized).

    FastAPI runs this automatically for routes that ask for it. Whatever we
    RETURN here gets passed into the route as the `current_user` argument."""

    # A reusable error to raise whenever the token is missing/invalid/expired.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired login. Please sign in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials  # the raw token string after the word "Bearer"

    try:
        payload = decode_access_token(token)  # verifies signature + expiry
        user_id = payload.get("sub")          # we stored the user id under "sub"
        if user_id is None:
            raise credentials_exception
    except Exception:
        # Any decoding problem (expired, tampered, garbage) lands here.
        raise credentials_exception

    # Look the user up in MongoDB by their id.
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise credentials_exception  # user was deleted after the token was issued

    return user
