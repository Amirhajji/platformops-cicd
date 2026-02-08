from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.db.models.users import User, Role


def assign_roles(db: Session, user_id: str, roles: List[str]):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.roles.clear()

    for role_id in roles:
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise HTTPException(status_code=400, detail=f"Invalid role {role_id}")
        user.roles.append(role)

    db.commit()
    return user
