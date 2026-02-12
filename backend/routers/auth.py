"""Authentication router."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from database import get_db
from auth import authenticate_user, create_access_token, create_token_pair, get_password_hash, get_current_active_user
from models import User
from schemas import TokenPair, UserCreate, UserResponse, UserLogin, RefreshTokenRequest
from config import settings

router = APIRouter()


@router.post("/login", response_model=TokenPair)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login endpoint. Returns access + refresh tokens."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return create_token_pair(user.username)


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(body.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type = payload.get("type")
        if token_type != "refresh":
            raise credentials_exception
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return create_token_pair(user.username)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if username exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password strength
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get current user information including org memberships."""
    from models import OrgMember, Organization
    memberships = db.query(OrgMember).filter(OrgMember.user_id == current_user.id).all()
    orgs = []
    for m in memberships:
        org = db.query(Organization).filter(Organization.id == m.org_id).first()
        if org:
            orgs.append({"id": str(org.id), "name": org.name, "slug": org.slug, "role": m.role})

    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_admin": current_user.is_admin,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "organizations": orgs,
    }


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """Logout endpoint (client should discard token)."""
    return {"message": "Successfully logged out"}
