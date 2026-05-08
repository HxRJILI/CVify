import random
import string
import bcrypt
from datetime import datetime, timedelta
from typing import Optional

from core.database import SessionLocal
from core.models import User, CVProfile, GeneratedCV

def generate_otp() -> str:
    """Generate a random 6-digit string."""
    return "".join(random.choices(string.digits, k=6))

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    """Check if a plaintext password matches the hashed password."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_user(email: str, password: str, full_name: str) -> User:
    """
    Creates a new user, hashes the password, and generates an OTP.
    Returns the created User object.
    """
    with SessionLocal() as db:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError("User with this email already exists.")
            
        otp = generate_otp()
        expiry = datetime.utcnow() + timedelta(minutes=15)
        
        new_user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            verification_code=otp,
            verification_expires_at=expiry,
            is_verified=False
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Initialize an empty CV profile for the new user
        new_profile = CVProfile(
            user_id=new_user.id,
            contact={
                "name": full_name,
                "email": email,
                "phone": "",
                "location": "",
                "linkedin": "",
                "portfolio": ""
            }
        )
        db.add(new_profile)
        db.commit()
        
        db.refresh(new_user)
        db.expunge(new_user)
        return new_user

def verify_user(email: str, otp: str) -> bool:
    """
    Verifies a user's email using the OTP.
    """
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise ValueError("User not found.")
            
        if user.is_verified:
            return True
            
        if user.verification_code != otp:
            raise ValueError("Invalid verification code.")
            
        if user.verification_expires_at and datetime.utcnow() > user.verification_expires_at:
            raise ValueError("Verification code has expired.")
            
        user.is_verified = True
        user.verification_code = None
        user.verification_expires_at = None
        db.commit()
        
        return True

def authenticate(email: str, password: str) -> Optional[User]:
    """
    Authenticates a user by email and password.
    Returns the User object if successful, or None.
    """
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
            
        if not check_password(password, user.password_hash):
            return None
            
        db.expunge(user)
        return user

def change_password(user_id: int, old_pw: str, new_pw: str) -> bool:
    """
    Validates old password, hashes new password, and saves it.
    Returns True on success, raises ValueError on failure.
    """
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found.")
            
        if not check_password(old_pw, user.password_hash):
            raise ValueError("Incorrect current password.")
            
        user.password_hash = hash_password(new_pw)
        db.commit()
        return True

def delete_account(user_id: int) -> bool:
    """
    Deletes a user account and all associated data.
    """
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
            
        # Due to cascade='all, delete-orphan' in models, 
        # deleting the user will remove CVProfile and GeneratedCV
        db.delete(user)
        db.commit()
        return True
