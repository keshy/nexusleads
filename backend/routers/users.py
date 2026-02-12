"""Users management router."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_active_user, get_password_hash
from models import User
from schemas import UserResponse, UserCreate, UserUpdate

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_active_user)):
    """Dependency to require admin access."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all users (admin only)."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new user (admin only)."""
    # Check if username exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        is_admin=False  # New users are not admin by default
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update current user's profile."""
    # Check if email is being changed and if it's already taken
    if user_data.email and user_data.email != current_user.email:
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = user_data.email
    
    # Update full name
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    
    # Update password if provided
    if user_data.password:
        current_user.password_hash = get_password_hash(user_data.password)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    db.delete(user)
    db.commit()
    
    return None
