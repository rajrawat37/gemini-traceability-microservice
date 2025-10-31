"""
GDPR Compliance Module
Implements user rights APIs as required by GDPR

Supported GDPR Articles:
- Art. 15: Right to access (get_user_data)
- Art. 16: Right to rectification (update_user_data)
- Art. 17: Right to erasure (delete_user_data)
- Art. 18: Right to restriction (restrict_user_processing)
- Art. 20: Right to data portability (export_user_data)
- Art. 7: Consent management (grant_consent, withdraw_consent, get_consent_status)
"""

import uuid
import json
import csv
import io
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import select, update, delete
from gdpr_database import (
    async_session_factory,
    User,
    UserData,
    ConsentRecord,
    AuditLog
)


# ==================== ARTICLE 15: RIGHT TO ACCESS ====================

async def get_user_data(user_id: str) -> Dict[str, Any]:
    """
    Art. 15 - Right to Access

    Retrieve all data stored for a specific user including:
    - User profile
    - Processed documents
    - Consent history
    - Processing activities

    Args:
        user_id: Unique user identifier

    Returns:
        Dictionary with all user data
    """
    async with async_session_factory() as session:
        # Get user
        result = await session.execute(select(User).filter_by(user_id=user_id))
        user = result.scalar_one_or_none()

        if not user:
            return {
                "status": "error",
                "error": "User not found",
                "gdpr_article": "Article 15 - Right to Access"
            }

        # Get all user data
        result = await session.execute(select(UserData).filter_by(user_id=user_id))
        user_data_records = result.scalars().all()

        result = await session.execute(select(ConsentRecord).filter_by(user_id=user_id))
        consent_records = result.scalars().all()

        result = await session.execute(
            select(AuditLog).filter_by(user_id=user_id).order_by(AuditLog.timestamp.desc()).limit(100)
        )
        audit_logs = result.scalars().all()

        return {
            "status": "success",
            "gdpr_article": "Article 15 - Right to Access",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "full_name": user.full_name,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "consent_status": user.consent_status,
                "data_restriction": user.data_restriction,
                "lawful_basis": user.lawful_basis
            },
            "statistics": {
                "total_documents_processed": len(user_data_records),
                "documents_with_pii": sum(1 for d in user_data_records if d.pii_detected),
                "consent_changes": len(consent_records),
                "processing_activities": len(audit_logs)
            },
            "documents": [
                {
                    "data_id": data.data_id,
                    "file_name": data.file_name,
                    "document_type": data.document_type,
                    "pii_detected": data.pii_detected,
                    "pii_types": data.pii_types,
                    "created_at": data.created_at.isoformat() if data.created_at else None,
                    "last_accessed": data.last_accessed.isoformat() if data.last_accessed else None
                }
                for data in user_data_records
            ],
            "consent_history": [
                {
                    "consent_id": consent.consent_id,
                    "consent_type": consent.consent_type,
                    "granted": consent.granted,
                    "timestamp": consent.timestamp.isoformat() if consent.timestamp else None,
                    "consent_version": consent.consent_version
                }
                for consent in consent_records
            ],
            "recent_processing_activities": [
                {
                    "log_id": log.log_id,
                    "action": log.action,
                    "endpoint": log.endpoint,
                    "data_type": log.data_type,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "success": log.success,
                    "legal_basis": log.legal_basis
                }
                for log in audit_logs[:20]  # Show most recent 20
            ]
        }


# ==================== ARTICLE 16: RIGHT TO RECTIFICATION ====================

async def update_user_data(
    user_id: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Art. 16 - Right to Rectification

    Allow users to correct inaccurate personal data

    Args:
        user_id: Unique user identifier
        email: New email address (optional)
        full_name: New full name (optional)

    Returns:
        Updated user data
    """
    async with async_session_factory() as session:
        result = await session.execute(select(User).filter_by(user_id=user_id))
        user = result.scalar_one_or_none()

        if not user:
            return {
                "status": "error",
                "error": "User not found",
                "gdpr_article": "Article 16 - Right to Rectification"
            }

        # Update fields
        if email:
            user.email = email
        if full_name:
            user.full_name = full_name

        user.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(user)

        return {
            "status": "success",
            "gdpr_article": "Article 16 - Right to Rectification",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "full_name": user.full_name,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            }
        }


# ==================== ARTICLE 17: RIGHT TO ERASURE ====================

async def delete_user_data(user_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Art. 17 - Right to Erasure ("Right to be Forgotten")

    Delete all user data and related records (cascade deletion)

    Args:
        user_id: Unique user identifier
        reason: Reason for deletion (optional, for audit purposes)

    Returns:
        Deletion confirmation
    """
    async with async_session_factory() as session:
        # Check if user exists
        result = await session.execute(select(User).filter_by(user_id=user_id))
        user = result.scalar_one_or_none()

        if not user:
            return {
                "status": "error",
                "error": "User not found",
                "gdpr_article": "Article 17 - Right to Erasure"
            }

        # Count records before deletion
        result = await session.execute(select(UserData).filter_by(user_id=user_id))
        data_count = len(result.scalars().all())

        result = await session.execute(select(ConsentRecord).filter_by(user_id=user_id))
        consent_count = len(result.scalars().all())

        result = await session.execute(select(AuditLog).filter_by(user_id=user_id))
        audit_count = len(result.scalars().all())

        # Create final audit log before deletion
        final_log = AuditLog(
            log_id=str(uuid.uuid4()),
            user_id=user_id,
            action="delete_user_data",
            endpoint="/user/{user_id}",
            data_type="all_user_data",
            success=True,
            timestamp=datetime.now(timezone.utc),
            legal_basis="user_request"
        )
        session.add(final_log)

        # Delete user (cascade will delete all related data)
        await session.execute(delete(User).filter_by(user_id=user_id))
        await session.commit()

        return {
            "status": "success",
            "gdpr_article": "Article 17 - Right to Erasure",
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "deletion_reason": reason or "User request",
            "deleted_records": {
                "user_profile": 1,
                "processed_documents": data_count,
                "consent_records": consent_count,
                "audit_logs": audit_count + 1  # +1 for final log
            },
            "confirmation": "All user data has been permanently deleted"
        }


# ==================== ARTICLE 18: RIGHT TO RESTRICTION ====================

async def restrict_user_processing(user_id: str, restrict: bool) -> Dict[str, Any]:
    """
    Art. 18 - Right to Restriction of Processing

    Allow users to restrict processing of their data
    When restricted, data is stored but not processed

    Args:
        user_id: Unique user identifier
        restrict: True to restrict, False to unrestrict

    Returns:
        Updated restriction status
    """
    async with async_session_factory() as session:
        result = await session.execute(select(User).filter_by(user_id=user_id))
        user = result.scalar_one_or_none()

        if not user:
            return {
                "status": "error",
                "error": "User not found",
                "gdpr_article": "Article 18 - Right to Restriction"
            }

        # Update restriction status
        user.data_restriction = restrict
        user.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(user)

        return {
            "status": "success",
            "gdpr_article": "Article 18 - Right to Restriction",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "data_restriction": user.data_restriction,
            "message": (
                "Data processing has been restricted. Your data will be stored but not processed."
                if restrict else
                "Data processing restriction has been lifted. Your data can now be processed."
            )
        }


# ==================== ARTICLE 20: RIGHT TO DATA PORTABILITY ====================

async def export_user_data(user_id: str, format: str = "json") -> Dict[str, Any]:
    """
    Art. 20 - Right to Data Portability

    Export all user data in machine-readable format (JSON or CSV)

    Args:
        user_id: Unique user identifier
        format: Export format ("json" or "csv")

    Returns:
        Exported data in requested format
    """
    async with async_session_factory() as session:
        # Get user
        result = await session.execute(select(User).filter_by(user_id=user_id))
        user = result.scalar_one_or_none()

        if not user:
            return {
                "status": "error",
                "error": "User not found",
                "gdpr_article": "Article 20 - Right to Data Portability"
            }

        # Get all related data
        result = await session.execute(select(UserData).filter_by(user_id=user_id))
        user_data_records = result.scalars().all()

        result = await session.execute(select(ConsentRecord).filter_by(user_id=user_id))
        consent_records = result.scalars().all()

        result = await session.execute(select(AuditLog).filter_by(user_id=user_id))
        audit_logs = result.scalars().all()

        # Build export data
        export_data = {
            "user_profile": {
                "user_id": user.user_id,
                "email": user.email,
                "full_name": user.full_name,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "consent_status": user.consent_status,
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
                    "consent_type": consent.consent_type,
                    "granted": consent.granted,
                    "timestamp": consent.timestamp.isoformat() if consent.timestamp else None,
                    "ip_address": consent.ip_address
                }
                for consent in consent_records
            ],
            "processing_activities": [
                {
                    "action": log.action,
                    "endpoint": log.endpoint,
                    "data_type": log.data_type,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "success": log.success
                }
                for log in audit_logs
            ],
            "export_metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "format": format,
                "gdpr_article": "Article 20 - Right to Data Portability"
            }
        }

        if format.lower() == "csv":
            # Convert to CSV format
            return _convert_to_csv(export_data)
        else:
            # Return JSON
            return {
                "status": "success",
                "gdpr_article": "Article 20 - Right to Data Portability",
                "format": "json",
                "data": export_data
            }


def _convert_to_csv(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert export data to CSV format"""

    # Create CSV for user profile
    profile_csv = io.StringIO()
    profile_writer = csv.DictWriter(profile_csv, fieldnames=export_data["user_profile"].keys())
    profile_writer.writeheader()
    profile_writer.writerow(export_data["user_profile"])

    # Create CSV for documents
    documents_csv = io.StringIO()
    if export_data["processed_documents"]:
        doc_writer = csv.DictWriter(
            documents_csv,
            fieldnames=["data_id", "file_name", "document_type", "pii_detected", "created_at"]
        )
        doc_writer.writeheader()
        for doc in export_data["processed_documents"]:
            doc_writer.writerow({
                "data_id": doc["data_id"],
                "file_name": doc["file_name"],
                "document_type": doc["document_type"],
                "pii_detected": doc["pii_detected"],
                "created_at": doc["created_at"]
            })

    return {
        "status": "success",
        "gdpr_article": "Article 20 - Right to Data Portability",
        "format": "csv",
        "files": {
            "user_profile.csv": profile_csv.getvalue(),
            "documents.csv": documents_csv.getvalue()
        }
    }


# ==================== ARTICLE 7: CONSENT MANAGEMENT ====================

async def grant_consent(
    user_id: str,
    consent_type: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    consent_version: str = "1.0"
) -> Dict[str, Any]:
    """
    Art. 7 - Consent Requirements

    Record user consent for specific processing activities

    Args:
        user_id: Unique user identifier
        consent_type: Type of consent ("data_processing", "marketing", "analytics")
        ip_address: User's IP address (for audit trail)
        user_agent: User's browser/client info
        consent_version: Version of privacy policy

    Returns:
        Consent record confirmation
    """
    async with async_session_factory() as session:
        # Verify user exists
        result = await session.execute(select(User).filter_by(user_id=user_id))
        user = result.scalar_one_or_none()

        if not user:
            return {
                "status": "error",
                "error": "User not found",
                "gdpr_article": "Article 7 - Consent"
            }

        # Create consent record
        consent = ConsentRecord(
            consent_id=str(uuid.uuid4()),
            user_id=user_id,
            consent_type=consent_type,
            granted=True,
            timestamp=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent,
            consent_version=consent_version
        )
        session.add(consent)

        # Update user consent status
        user.consent_status = True
        user.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(consent)

        return {
            "status": "success",
            "gdpr_article": "Article 7 - Consent",
            "consent_id": consent.consent_id,
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": True,
            "timestamp": consent.timestamp.isoformat(),
            "consent_version": consent_version
        }


async def withdraw_consent(
    user_id: str,
    consent_type: str,
    ip_address: Optional[str] = None
) -> Dict[str, Any]:
    """
    Art. 7(3) - Right to Withdraw Consent

    Record withdrawal of consent

    Args:
        user_id: Unique user identifier
        consent_type: Type of consent to withdraw
        ip_address: User's IP address

    Returns:
        Withdrawal confirmation
    """
    async with async_session_factory() as session:
        # Create withdrawal record
        withdrawal = ConsentRecord(
            consent_id=str(uuid.uuid4()),
            user_id=user_id,
            consent_type=consent_type,
            granted=False,  # False = withdrawal
            timestamp=datetime.now(timezone.utc),
            ip_address=ip_address
        )
        session.add(withdrawal)
        await session.commit()

        return {
            "status": "success",
            "gdpr_article": "Article 7(3) - Withdrawal of Consent",
            "consent_id": withdrawal.consent_id,
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": False,
            "timestamp": withdrawal.timestamp.isoformat(),
            "message": f"Consent for '{consent_type}' has been withdrawn"
        }


async def get_consent_status(user_id: str) -> Dict[str, Any]:
    """
    Get current consent status for a user

    Args:
        user_id: Unique user identifier

    Returns:
        Consent status for all types
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(ConsentRecord)
            .filter_by(user_id=user_id)
            .order_by(ConsentRecord.timestamp.desc())
        )
        records = result.scalars().all()

        if not records:
            return {
                "status": "error",
                "error": "No consent records found",
                "user_id": user_id
            }

        # Get latest consent for each type
        consent_by_type = {}
        for record in records:
            if record.consent_type not in consent_by_type:
                consent_by_type[record.consent_type] = {
                    "granted": record.granted,
                    "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                    "consent_version": record.consent_version
                }

        return {
            "status": "success",
            "user_id": user_id,
            "consents": consent_by_type,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }


# ==================== HELPER FUNCTIONS ====================

async def check_user_consent(user_id: str, consent_type: str) -> bool:
    """
    Check if user has granted specific consent

    Args:
        user_id: Unique user identifier
        consent_type: Type of consent to check

    Returns:
        True if consent granted, False otherwise
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(ConsentRecord)
            .filter_by(user_id=user_id, consent_type=consent_type)
            .order_by(ConsentRecord.timestamp.desc())
            .limit(1)
        )
        latest_consent = result.scalar_one_or_none()

        if not latest_consent:
            return False

        return latest_consent.granted


async def check_data_restriction(user_id: str) -> bool:
    """
    Check if user has restricted data processing

    Args:
        user_id: Unique user identifier

    Returns:
        True if restricted, False otherwise
    """
    async with async_session_factory() as session:
        result = await session.execute(select(User).filter_by(user_id=user_id))
        user = result.scalar_one_or_none()

        if not user:
            return False

        return user.data_restriction
