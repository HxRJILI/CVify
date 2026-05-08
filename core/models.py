from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from core.database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150))
    is_verified = Column(Boolean, default=False)
    verification_code = Column(String(6))
    verification_expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    cv_profile = relationship("CVProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    generated_cvs = relationship("GeneratedCV", back_populates="user", cascade="all, delete-orphan")

class CVProfile(Base):
    __tablename__ = 'cv_profiles'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    photo_path = Column(String(500))
    contact = Column(JSON)
    summary = Column(Text)
    work_experience = Column(JSON)
    education = Column(JSON)
    skills_hard = Column(JSON)
    skills_soft = Column(JSON)
    certifications = Column(JSON)
    projects = Column(JSON)
    awards = Column(JSON)
    volunteer = Column(JSON)
    languages = Column(JSON)
    publications = Column(JSON)
    affiliations = Column(JSON)
    interests = Column(JSON)
    conferences = Column(JSON)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="cv_profile")

class GeneratedCV(Base):
    __tablename__ = 'generated_cvs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    template_id = Column(String(50))
    job_title = Column(String(200))
    job_description = Column(Text)
    match_score = Column(Integer)
    match_summary = Column(Text)
    sections_included = Column(JSON)
    latex_source = Column(Text)
    pdf_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="generated_cvs")
