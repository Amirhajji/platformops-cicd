# app/api/auth.py
from http.client import HTTPException
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.models.users import User
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse, UserInfo
from app.services.auth_service import signup, login
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from jose import JWTError
from app.core.security import decode_email_verification_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup")
def signup_api(req: SignupRequest, db: Session = Depends(get_db)):
    user = signup(db, req.username, req.password)
    return {"id": str(user.id), "username": user.username}


@router.post("/login", response_model=TokenResponse)
def login_api(req: LoginRequest, db: Session = Depends(get_db)):
    token = login(db, req.username, req.password)
    return {"access_token": token}


@router.get("/me", response_model=UserInfo)
def me(user=Depends(get_current_user)):
    return {
        "id": str(user.id),
        "username": user.username,
        "roles": user.roles_from_token,
        "is_active": user.is_active,
    }





@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        payload = decode_email_verification_token(token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_active:
        return {"message": "Account already verified"}

    user.is_active = True
    db.commit()

    return {"message": "Account verified successfully"}
