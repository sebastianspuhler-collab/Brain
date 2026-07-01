from fastapi import HTTPException, Request

from app.security import SESSION_COOKIE, read_session_token


def get_current_user(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="unauthorized")
    user = read_session_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="unauthorized")
    return user
