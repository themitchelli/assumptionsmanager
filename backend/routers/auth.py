import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from models import User, Tenant
from schemas import UserCreate, UserResponse, UserLogin, Token
from auth import hash_password, verify_password, create_access_token, get_current_user, TokenData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Registration failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


@router.post("/login", response_model=Token)
def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    try:
        # Find user by email
        user = db.execute(
            select(User).where(User.email == credentials.email)
        ).scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Verify password
        if not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Check if tenant is active
        tenant = db.execute(
            select(Tenant).where(Tenant.id == user.tenant_id)
        ).scalar_one_or_none()

        if tenant and tenant.status == "inactive":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account suspended. Please contact your administrator.",
            )

        # Create JWT token
        access_token = create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            role=user.role,
        )

        return Token(access_token=access_token)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Login failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}",
        )


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user = db.execute(
            select(User).where(User.id == current_user.user_id)
        ).scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Get current user failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get current user failed: {str(e)}",
        )
