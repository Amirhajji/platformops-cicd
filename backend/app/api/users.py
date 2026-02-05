# app/api/users.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.schemas.user import AssignRolesRequest
from app.services.user_service import assign_roles
from app.db.models.users import User

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/")
def list_users(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "roles": [r.id for r in u.roles],
            "is_active": u.is_active,
        }
        for u in db.query(User).all()
    ]


@router.post("/{user_id}/roles")
def set_roles(
    user_id: str,
    req: AssignRolesRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    user = assign_roles(db, user_id, req.roles)
    return {"id": str(user.id), "roles": [r.id for r in user.roles]}
