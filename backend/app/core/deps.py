from fastapi import Depends, HTTPException, status
from app.core.security import get_current_user
from app.models.role import Role


def require_role(*allowed_roles):
    allowed_values = {r.value if isinstance(r, Role) else r for r in allowed_roles}

    async def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_user
    return role_checker


require_admin = require_role(Role.ADMIN)
require_editor = require_role(Role.ADMIN, Role.EDITOR)
require_reviewer = require_role(Role.ADMIN, Role.EDITOR, Role.REVIEWER)
require_viewer = require_role(Role.ADMIN, Role.EDITOR, Role.REVIEWER, Role.VIEWER)
