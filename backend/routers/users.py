from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user, TokenData
from schemas import UserResponse, UserRoleUpdate

router = APIRouter(prefix="/users", tags=["users"])

VALID_ROLES = {"viewer", "analyst", "admin"}


@router.get("", response_model=list[UserResponse])
async def list_users(current_user: TokenData = Depends(get_current_user)):
    """List all users in the current tenant"""
    try:
        db = SessionLocal()
        try:
            result = db.execute(
                text("SELECT id, tenant_id, email, role, created_at FROM users WHERE tenant_id = :tenant_id"),
                {"tenant_id": str(current_user.tenant_id)}
            )
            users = [
                UserResponse(
                    id=row[0],
                    tenant_id=row[1],
                    email=row[2],
                    role=row[3],
                    created_at=row[4]
                )
                for row in result
            ]
            return users
        finally:
            db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user_role(
    user_id: UUID,
    update: UserRoleUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Update a user's role (admin only)"""
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=403,
            detail="Only admin can update user roles"
        )

    if update.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}"
        )

    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot change your own role"
        )

    try:
        db = SessionLocal()
        try:
            # Check user exists and is in same tenant
            result = db.execute(
                text("SELECT id, tenant_id, email, role, created_at FROM users WHERE id = :user_id AND tenant_id = :tenant_id"),
                {"user_id": str(user_id), "tenant_id": str(current_user.tenant_id)}
            )
            user = result.fetchone()

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Update role
            db.execute(
                text("UPDATE users SET role = :role, updated_at = NOW() WHERE id = :user_id"),
                {"role": update.role, "user_id": str(user_id)}
            )
            db.commit()

            return UserResponse(
                id=user[0],
                tenant_id=user[1],
                email=user[2],
                role=update.role,
                created_at=user[4]
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete a user (admin only)"""
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=403,
            detail="Only admin can delete users"
        )

    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete yourself"
        )

    try:
        db = SessionLocal()
        try:
            # Check user exists and is in same tenant
            result = db.execute(
                text("SELECT id FROM users WHERE id = :user_id AND tenant_id = :tenant_id"),
                {"user_id": str(user_id), "tenant_id": str(current_user.tenant_id)}
            )
            user = result.fetchone()

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Delete user
            db.execute(
                text("DELETE FROM users WHERE id = :user_id"),
                {"user_id": str(user_id)}
            )
            db.commit()
            return None
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
