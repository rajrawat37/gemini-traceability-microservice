"""
GDPR Compliance Database Schema
SQLite database for managing user data, consent, and audit trails

GDPR Articles Supported:
- Art. 15: Right to access (user_data table)
- Art. 16: Right to rectification (users table)
- Art. 17: Right to erasure (cascade deletions)
- Art. 18: Right to restriction (data_restriction flag)
- Art. 7: Consent records (consent_records table)
- Art. 30: Records of processing (audit_logs table)
- Art. 33: Breach notification (breach_alerts table)
"""

import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base as async_declarative_base
import json

# Database file location
DB_FILE = os.getenv("GDPR_DB_PATH", "gdpr_data.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_FILE}"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    future=True
)

# Session factory
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = async_declarative_base()


# ==================== MODELS ====================

class User(Base):
    """
    User table - stores user profile and consent status

    GDPR Articles:
    - Art. 6: Lawful basis for processing
    - Art. 16: Right to rectification (can update fields)
    - Art. 17: Right to erasure (cascade delete)
    - Art. 18: Right to restriction (data_restriction flag)
    """
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # GDPR-specific fields
    consent_status = Column(Boolean, default=False, nullable=False)  # Art. 7: Consent
    data_restriction = Column(Boolean, default=False, nullable=False)  # Art. 18: Restriction
    lawful_basis = Column(String, default="consent", nullable=False)  # Art. 6: Legal basis

    # Relationships (cascade delete for Art. 17: Right to erasure)
    user_data = relationship("UserData", back_populates="user", cascade="all, delete-orphan")
    consent_records = relationship("ConsentRecord", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


class UserData(Base):
    """
    User data table - stores processed documents and results

    GDPR Articles:
    - Art. 15: Right to access (users can retrieve this data)
    - Art. 17: Right to erasure (deleted with user)
    - Art. 20: Right to data portability (exported as JSON/CSV)
    """
    __tablename__ = "user_data"

    data_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Document metadata
    file_name = Column(String, nullable=False)
    document_type = Column(String, default="pdf", nullable=False)

    # Processing results (encrypted JSON)
    processed_data = Column(JSON, nullable=True)  # Stores full pipeline output

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_accessed = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # GDPR metadata
    pii_detected = Column(Boolean, default=False, nullable=False)
    pii_types = Column(JSON, nullable=True)  # List of PII types found

    # Relationship
    user = relationship("User", back_populates="user_data")


class ConsentRecord(Base):
    """
    Consent records table - tracks user consent history

    GDPR Articles:
    - Art. 7: Consent requirements (proof of consent)
    - Art. 7(3): Right to withdraw consent
    """
    __tablename__ = "consent_records"

    consent_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Consent details
    consent_type = Column(String, nullable=False)  # "data_processing", "marketing", "analytics", etc.
    granted = Column(Boolean, nullable=False)  # True = granted, False = withdrawn

    # Audit trail
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # Legal basis
    consent_version = Column(String, default="1.0", nullable=False)  # Version of privacy policy

    # Relationship
    user = relationship("User", back_populates="consent_records")


class AuditLog(Base):
    """
    Audit logs table - tracks all data access and processing

    GDPR Articles:
    - Art. 30: Records of processing activities
    - Art. 32: Security of processing (monitoring)
    """
    __tablename__ = "audit_logs"

    log_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True, index=True)

    # Action details
    action = Column(String, nullable=False)  # "read", "write", "delete", "export", "restrict"
    endpoint = Column(String, nullable=False)  # API endpoint called
    data_type = Column(String, nullable=True)  # "pdf_document", "test_results", "knowledge_graph", etc.

    # Result
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)

    # Audit trail
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # Legal basis for this action
    legal_basis = Column(String, nullable=False)  # "consent", "contract", "legitimate_interest"

    # Relationship
    user = relationship("User", back_populates="audit_logs")


class BreachAlert(Base):
    """
    Breach alerts table - tracks security incidents

    GDPR Articles:
    - Art. 33: Notification of breach to supervisory authority
    - Art. 34: Communication of breach to data subject
    """
    __tablename__ = "breach_alerts"

    alert_id = Column(String, primary_key=True)

    # Alert details
    alert_type = Column(String, nullable=False)  # "rate_limit_exceeded", "failed_auth", "unusual_access"
    severity = Column(String, nullable=False)  # "low", "medium", "high", "critical"

    # Incident details
    description = Column(Text, nullable=False)
    affected_users = Column(JSON, nullable=True)  # List of user_ids
    ip_address = Column(String, nullable=True)

    # Response
    notified = Column(Boolean, default=False, nullable=False)
    notification_timestamp = Column(DateTime, nullable=True)
    resolved = Column(Boolean, default=False, nullable=False)
    resolution_notes = Column(Text, nullable=True)

    # Timestamps
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)


# ==================== DATABASE INITIALIZATION ====================

async def init_database():
    """
    Initialize database tables
    Creates all tables if they don't exist
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ GDPR database initialized successfully")


async def get_session() -> AsyncSession:
    """
    Get async database session
    Usage: async with get_session() as session: ...
    """
    async with async_session_factory() as session:
        yield session


# ==================== HELPER FUNCTIONS ====================

async def create_user(user_id: str, email: str, full_name: Optional[str] = None) -> User:
    """Create new user with default consent"""
    from sqlalchemy import select

    async with async_session_factory() as session:
        # Check if user exists
        result = await session.execute(select(User).filter_by(user_id=user_id))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            return existing_user

        # Create new user
        user = User(
            user_id=user_id,
            email=email,
            full_name=full_name,
            consent_status=False,  # Must explicitly grant consent
            lawful_basis="consent"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def delete_user(user_id: str) -> bool:
    """
    Delete user and all associated data (cascade)
    Implements Art. 17: Right to erasure
    """
    from sqlalchemy import select, delete

    async with async_session_factory() as session:
        # Delete user (cascade will delete related data)
        result = await session.execute(delete(User).filter_by(user_id=user_id))
        await session.commit()
        return result.rowcount > 0


async def get_user_data_export(user_id: str) -> Dict[str, Any]:
    """
    Export all user data in machine-readable format
    Implements Art. 20: Right to data portability
    """
    from sqlalchemy import select

    async with async_session_factory() as session:
        # Get user
        result = await session.execute(select(User).filter_by(user_id=user_id))
        user = result.scalar_one_or_none()

        if not user:
            return {"error": "User not found"}

        # Get all related data
        result = await session.execute(select(UserData).filter_by(user_id=user_id))
        user_data_records = result.scalars().all()

        result = await session.execute(select(ConsentRecord).filter_by(user_id=user_id))
        consent_records = result.scalars().all()

        result = await session.execute(select(AuditLog).filter_by(user_id=user_id))
        audit_logs = result.scalars().all()

        # Build export
        export = {
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "full_name": user.full_name,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "consent_status": user.consent_status,
                "data_restriction": user.data_restriction,
                "lawful_basis": user.lawful_basis
            },
            "processed_documents": [
                {
                    "data_id": data.data_id,
                    "file_name": data.file_name,
                    "document_type": data.document_type,
                    "processed_data": data.processed_data,
                    "pii_detected": data.pii_detected,
                    "pii_types": data.pii_types,
                    "created_at": data.created_at.isoformat() if data.created_at else None
                }
                for data in user_data_records
            ],
            "consent_history": [
                {
                    "consent_id": consent.consent_id,
                    "consent_type": consent.consent_type,
                    "granted": consent.granted,
                    "timestamp": consent.timestamp.isoformat() if consent.timestamp else None,
                    "ip_address": consent.ip_address
                }
                for consent in consent_records
            ],
            "audit_trail": [
                {
                    "log_id": log.log_id,
                    "action": log.action,
                    "endpoint": log.endpoint,
                    "data_type": log.data_type,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "legal_basis": log.legal_basis
                }
                for log in audit_logs
            ],
            "export_metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "format": "JSON",
                "gdpr_article": "Article 20 - Right to Data Portability"
            }
        }

        return export


# Initialize database on module import
if __name__ == "__main__":
    import asyncio
    asyncio.run(init_database())
    print(f"📁 Database file: {DB_FILE}")
