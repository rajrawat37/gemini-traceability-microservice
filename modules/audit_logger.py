"""
GDPR Audit Logger Module
Implements comprehensive audit logging for compliance

GDPR Article Supported:
- Art. 30: Records of Processing Activities (ROPA)

Features:
- Logs every data access and modification
- Tracks legal basis for each action
- Stores IP address and user agent for accountability
- Provides queryable audit trail for compliance audits
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from gdpr_database import async_session_factory, AuditLog


# ==================== AUDIT LOGGING ====================

async def log_audit(
    user_id: Optional[str],
    action: str,
    endpoint: str,
    data_type: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    legal_basis: str = "consent"
) -> str:
    """
    Art. 30 - Records of Processing Activities

    Log every data processing activity for GDPR compliance

    Args:
        user_id: User whose data is being processed (can be None for system actions)
        action: Type of action ("read", "write", "delete", "export", "restrict")
        endpoint: API endpoint called
        data_type: Type of data processed ("pdf_document", "test_results", etc.)
        success: Whether the action succeeded
        error_message: Error message if action failed
        ip_address: Client IP address
        user_agent: Client user agent string
        legal_basis: Legal basis for processing ("consent", "contract", "legitimate_interest")

    Returns:
        log_id: Unique identifier for this log entry
    """
    log_id = str(uuid.uuid4())

    async with async_session_factory() as session:
        audit_log = AuditLog(
            log_id=log_id,
            user_id=user_id,
            action=action,
            endpoint=endpoint,
            data_type=data_type,
            success=success,
            error_message=error_message,
            timestamp=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent,
            legal_basis=legal_basis
        )

        session.add(audit_log)
        await session.commit()

    return log_id


async def get_audit_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100
) -> list:
    """
    Query audit logs with filters

    Args:
        user_id: Filter by user (optional)
        action: Filter by action type (optional)
        start_date: Filter by start date (optional)
        end_date: Filter by end date (optional)
        limit: Maximum number of results

    Returns:
        List of audit log entries
    """
    async with async_session_factory() as session:
        query = select(AuditLog)

        # Apply filters
        if user_id:
            query = query.filter_by(user_id=user_id)
        if action:
            query = query.filter_by(action=action)
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        # Order by timestamp descending and limit
        query = query.order_by(AuditLog.timestamp.desc()).limit(limit)

        result = await session.execute(query)
        logs = result.scalars().all()

        return [
            {
                "log_id": log.log_id,
                "user_id": log.user_id,
                "action": log.action,
                "endpoint": log.endpoint,
                "data_type": log.data_type,
                "success": log.success,
                "error_message": log.error_message,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "ip_address": log.ip_address,
                "legal_basis": log.legal_basis
            }
            for log in logs
        ]


async def get_processing_statistics(user_id: Optional[str] = None) -> dict:
    """
    Get processing activity statistics for ROPA reports

    Args:
        user_id: User ID to get stats for (or None for all users)

    Returns:
        Dictionary with processing statistics
    """
    from sqlalchemy import func

    async with async_session_factory() as session:
        query = select(
            func.count(AuditLog.log_id).label("total_actions"),
            func.count(func.distinct(AuditLog.user_id)).label("unique_users"),
            AuditLog.action,
            AuditLog.data_type,
            AuditLog.legal_basis
        ).group_by(AuditLog.action, AuditLog.data_type, AuditLog.legal_basis)

        if user_id:
            query = query.filter_by(user_id=user_id)

        result = await session.execute(query)
        rows = result.fetchall()

        # Aggregate by action type
        action_stats = {}
        for row in rows:
            action = row.action
            if action not in action_stats:
                action_stats[action] = {
                    "total_count": 0,
                    "data_types": {},
                    "legal_bases": {}
                }

            action_stats[action]["total_count"] += row.total_actions
            action_stats[action]["data_types"][row.data_type] = action_stats[action]["data_types"].get(row.data_type, 0) + row.total_actions
            action_stats[action]["legal_bases"][row.legal_basis] = action_stats[action]["legal_bases"].get(row.legal_basis, 0) + row.total_actions

        return {
            "status": "success",
            "gdpr_article": "Article 30 - Records of Processing Activities",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "statistics": action_stats
        }


# ==================== HELPER FUNCTIONS ====================

def get_client_ip(request) -> Optional[str]:
    """
    Extract client IP address from request

    Args:
        request: FastAPI Request object

    Returns:
        IP address string or None
    """
    # Try to get IP from X-Forwarded-For header (for proxies/load balancers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, get the first one
        return forwarded_for.split(",")[0].strip()

    # Fallback to direct client IP
    return request.client.host if request.client else None


def get_user_agent(request) -> Optional[str]:
    """
    Extract user agent from request

    Args:
        request: FastAPI Request object

    Returns:
        User agent string or None
    """
    return request.headers.get("User-Agent")


# ==================== ROPA REPORT GENERATION ====================

async def generate_ropa_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> dict:
    """
    Generate Records of Processing Activities (ROPA) report

    Art. 30 requires documentation of:
    - Name and contact details of controller
    - Purposes of processing
    - Categories of data subjects
    - Categories of personal data
    - Categories of recipients
    - Data retention periods
    - Security measures

    Args:
        start_date: Report start date (optional)
        end_date: Report end date (optional)

    Returns:
        ROPA-compliant report
    """
    from sqlalchemy import func

    async with async_session_factory() as session:
        # Query for processing activities
        query = select(
            AuditLog.action,
            AuditLog.data_type,
            AuditLog.legal_basis,
            func.count(AuditLog.log_id).label("count"),
            func.count(func.distinct(AuditLog.user_id)).label("affected_users")
        ).group_by(AuditLog.action, AuditLog.data_type, AuditLog.legal_basis)

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        result = await session.execute(query)
        rows = result.fetchall()

        # Build ROPA report
        processing_activities = []
        for row in rows:
            activity = {
                "processing_activity": row.action,
                "data_category": row.data_type or "general_data",
                "legal_basis": row.legal_basis,
                "number_of_operations": row.count,
                "data_subjects_affected": row.affected_users,
                "purpose": _get_purpose_for_action(row.action),
                "retention_period": _get_retention_period(row.data_type),
                "security_measures": [
                    "PII masking with Google DLP",
                    "Encryption at rest and in transit",
                    "Access control and authentication",
                    "Audit logging of all operations"
                ]
            }
            processing_activities.append(activity)

        return {
            "status": "success",
            "report_type": "Records of Processing Activities (ROPA)",
            "gdpr_article": "Article 30",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_period": {
                "start_date": start_date.isoformat() if start_date else "inception",
                "end_date": end_date.isoformat() if end_date else "current"
            },
            "controller_details": {
                "name": "PDF Processor API",
                "contact": "dpo@example.com",  # Replace with actual DPO contact
                "representative": "Data Protection Officer"
            },
            "processing_activities": processing_activities,
            "total_activities": len(processing_activities),
            "compliance_notes": [
                "All processing activities are logged with timestamp and legal basis",
                "Users can exercise their rights (access, erasure, portability, etc.)",
                "Consent is tracked and can be withdrawn at any time",
                "Data breaches are detected and logged for 72-hour notification"
            ]
        }


def _get_purpose_for_action(action: str) -> str:
    """Map action to processing purpose"""
    purposes = {
        "read": "Providing service to data subject",
        "write": "Storing user data for service delivery",
        "delete": "Fulfilling right to erasure",
        "export": "Fulfilling right to data portability",
        "restrict": "Fulfilling right to restriction of processing",
        "document_processing": "Compliance analysis and test generation"
    }
    return purposes.get(action, "Service delivery")


def _get_retention_period(data_type: Optional[str]) -> str:
    """Get retention period for data type"""
    retention_periods = {
        "pdf_document": "Until user requests deletion",
        "test_results": "Until user requests deletion",
        "knowledge_graph": "Until user requests deletion",
        "audit_logs": "3 years (legal requirement)",
        "consent_records": "3 years after withdrawal"
    }
    return retention_periods.get(data_type or "general_data", "Until user requests deletion")
