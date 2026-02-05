# app/schemas/user.py
from pydantic import BaseModel
from typing import List


class AssignRolesRequest(BaseModel):
    roles: List[str]
