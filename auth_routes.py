# auth_routes.py
# -----------------------------------------------------------------------------
# These are the web endpoints (URLs) for creating an account and logging in:
#   POST /auth/signup  -> make a new user
#   POST /auth/login   -> check email+password and hand back a login token
#
# An "APIRouter" is just a group of related routes. In main.py we plug this
# router into the app under the "/auth" prefix.
# -----------------------------------------------------------------------------

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pymongo.errors import DuplicateKeyError

from database import users_collection
from models import SignupRequest, LoginRequest, TokenResponse
from security import hash_password, verify_password, create_access_token

# All routes below automatically start with /auth and are tagged "auth" in docs.
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
def signup(data: SignupRequest):
    """Create a brand-new user, then log them in immediately by returning a token.

    `data` arrives already validated by Pydantic (see models.py), so we know
    name/email/password exist and look reasonable."""

    # Build the user "document" (a dictionary) to store in MongoDB.
    # NOTE: we store the HASH of the password, never the password itself.
    user_doc = {
        "name": data.name,
        "email": data.email.lower(),        # store lowercase so Email == email
        "password": hash_password(data.password),
        "created_at": datetime.now(timezone.utc),
    }

    try:
        # insert_one saves the document. Because we set a unique index on email
        # in database.py, MongoDB will reject a second signup with the same email.
        result = users_collection.insert_one(user_doc)
    except DuplicateKeyError:
        # This fires when the email already exists.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists. Please log in.",
        )

    # result.inserted_id is the new user's unique id. We turn it into a string
    # to put inside the token.
    user_id = str(result.inserted_id)
    token = create_access_token(user_id=user_id, email=data.email.lower())

    return TokenResponse(access_token=token, name=data.name)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    """Check the email + password. If correct, return a fresh login token."""

    # Find the user by email.
    user = users_collection.find_one({"email": data.email.lower()})

    # We deliberately give the SAME vague message whether the email is unknown
    # or the password is wrong. This avoids telling attackers which emails exist.
    if user is None or not verify_password(data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    user_id = str(user["_id"])
    token = create_access_token(user_id=user_id, email=user["email"])

    return TokenResponse(access_token=token, name=user["name"])
