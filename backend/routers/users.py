import secrets
import string
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user, TokenData, hash_password
from schemas import UserResponse, UserRoleUpdate, UserCreateByAdmin

router = APIRouter(prefix="/users", tags=["users"])

VALID_ROLES = {"viewer", "analyst", "admin"}


def generate_temp_password(length: int = 16) -> str:
    """Generate a secure temporary password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


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


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateByAdmin,
    current_user: TokenData = Depends(get_current_user)
):
    """Create a new user in the current tenant (admin only).

    Generates a temporary password for the user. In production,
    an email would be sent with password reset instructions.
    """
    # Only admin or super_admin can create users
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can create users"
        )

    # Validate role
    if user_data.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}"
        )

    try:
        db = SessionLocal()
        try:
            # Check for duplicate email within tenant
            result = db.execute(
                text("SELECT id FROM users WHERE email = :email AND tenant_id = :tenant_id"),
                {"email": user_data.email, "tenant_id": str(current_user.tenant_id)}
            )
            if result.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A user with this email already exists in your organization"
                )

            # Generate temporary password
            temp_password = generate_temp_password()
            password_hash = hash_password(temp_password)

            # Create user
            result = db.execute(
                text("""
                    INSERT INTO users (tenant_id, email, password_hash, role)
                    VALUES (:tenant_id, :email, :password_hash, :role)
                    RETURNING id, tenant_id, email, role, created_at
                """),
                {
                    "tenant_id": str(current_user.tenant_id),
                    "email": user_data.email,
                    "password_hash": password_hash,
                    "role": user_data.role
                }
            )
            row = result.fetchone()
            db.commit()

            # Note: In production, send email with temp_password to user_data.email
            # For now, the user would need to use password reset flow

            return UserResponse(
                id=row[0],
                tenant_id=row[1],
                email=row[2],
                role=row[3],
                created_at=row[4]
            )
        finally:
            db.close()
    except HTTPException:
        raise
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
    """Delete a user (admin only, super_admin can delete admins)"""
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
            # Check user exists and is in same tenant, get their role
            result = db.execute(
                text("SELECT id, role FROM users WHERE id = :user_id AND tenant_id = :tenant_id"),
                {"user_id": str(user_id), "tenant_id": str(current_user.tenant_id)}
            )
            user = result.fetchone()

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Admins cannot delete other admins (only super_admin can)
            target_role = user[1]
            if target_role == "admin" and current_user.role != "super_admin":
                raise HTTPException(
                    status_code=403,
                    detail="Only super admin can delete other admins"
                )

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
