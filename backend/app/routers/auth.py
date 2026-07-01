from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.deps import get_current_user
from app.security import (
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    create_session_token,
    verify_password,
)
from app.users import get_password_hash, user_exists

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, response: Response, body: LoginRequest):
    if not user_exists(body.username):
        raise HTTPException(status_code=401, detail="invalid credentials")
    stored_hash = get_password_hash(body.username)
    if not stored_hash or not verify_password(body.password, stored_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")

    token = create_session_token(body.username)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return {"ok": True, "user": body.username}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: str = Depends(get_current_user)):
    return {"user": user}
