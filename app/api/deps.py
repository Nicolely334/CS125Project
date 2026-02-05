from fastapi import Header, HTTPException
from app.core.security import extract_bearer_token, verify_supabase_jwt


def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    token = extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    try:
        claims = verify_supabase_jwt(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim")
    return user_id
