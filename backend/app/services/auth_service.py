# app/services/auth_service.py
from sqlalchemy.orm import Session
from app.db.models.users import User, Role
from app.core.security import hash_password, verify_password, create_access_token
from fastapi import HTTPException
from app.services.email_service import send_email
from app.core.security import create_email_verification_token
from app.core.config import settings



def signup(db: Session, username: str, password: str):
    if db.query(User).filter_by(username=username).first():
        raise HTTPException(status_code=400, detail="Username exists")

    user = User(
        username=username,
        password_hash=hash_password(password),
        is_active=False,  # 🔒 NOT ACTIVE YET
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_email_verification_token({
        "sub": str(user.id),
        "username": user.username,
    })

    verify_url = (
        f"{settings.APP_PUBLIC_BASE_URL}"
        f"/api/auth/verify-email?token={token}"
    )

    send_email(
        to_email=user.username,  # username = email
        subject="Verify your PlatformOPS account",
        text=f"Verify your account: {verify_url}",
        html=f"""
        <h2>Welcome to PlatformOPS</h2>
        <p>Please verify your account:</p>
        <a href="{verify_url}">Verify Email</a>
        """,
    )

    return user


def login(db: Session, username: str, password: str):
    user = db.query(User).filter_by(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account not verified. Check your email.",
        )

    roles = [r.id for r in user.roles]
    is_admin = "admin" in roles

    token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "roles": roles,
        "is_admin": is_admin,
    })

    return token













