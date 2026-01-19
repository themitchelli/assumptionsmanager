from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from models import User, Tenant
from schemas import UserCreate, UserResponse
from auth import hash_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # Verify tenant exists
    tenant = db.execute(
        select(Tenant).where(Tenant.id == user_data.tenant_id)
    ).scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Check for duplicate email within tenant
    existing_user = db.execute(
        select(User).where(
            User.tenant_id == user_data.tenant_id, User.email == user_data.email
        )
    ).scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered for this tenant",
        )

    # Create user with hashed password
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        tenant_id=user_data.tenant_id,
        role="viewer",
    )

    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered for this tenant",
        )

    return user
