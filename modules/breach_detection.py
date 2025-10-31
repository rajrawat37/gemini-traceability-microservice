"""
GDPR Breach Detection Module
Implements security monitoring and breach notification

GDPR Articles Supported:
- Art. 33: Notification of a personal data breach to the supervisory authority
- Art. 34: Communication of a personal data breach to the data subject
- Art. 32: Security of processing

Features:
- Rate limiting (prevent brute force attacks)
- Failed authentication tracking
- Unusual access pattern detection
- Automated breach alerts
- 72-hour notification tracking
"""

import uuid
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from collections import defaultdict
import asyncio
from sqlalchemy import select, func
from gdpr_database import async_session_factory, BreachAlert, AuditLog


# ==================== CONFIGURATION ====================

# Rate limiting thresholds
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "100"))
MAX_REQUESTS_PER_HOUR = int(os.getenv("MAX_REQUESTS_PER_HOUR", "1000"))

# Authentication failure thresholds
MAX_AUTH_FAILURES = int(os.getenv("MAX_AUTH_FAILURES", "5"))
AUTH_FAILURE_WINDOW_MINUTES = 15

# Unusual access thresholds
BUSINESS_HOURS_START = 6  # 6 AM
BUSINESS_HOURS_END = 22   # 10 PM


# ==================== IN-MEMORY TRACKING ====================

# Track requests per IP (in-memory for speed)
_ip_request_tracker = defaultdict(list)
_ip_auth_failures = defaultdict(list)


# ==================== RATE LIMITING ====================

async def check_rate_limit(ip_address: str) -> tuple[bool, Optional[str]]:
    """
    Check if IP address has exceeded rate limits

    Args:
        ip_address: Client IP address

    Returns:
        Tuple of (is_allowed, error_message)
    """
    now = datetime.now(timezone.utc)
    cutoff_minute = now - timedelta(minutes=1)
    cutoff_hour = now - timedelta(hours=1)

    # Get requests for this IP
    requests = _ip_request_tracker[ip_address]

    # Clean old entries (older than 1 hour)
    requests = [req_time for req_time in requests if req_time > cutoff_hour]
    _ip_request_tracker[ip_address] = requests

    # Count requests in last minute and hour
    requests_last_minute = sum(1 for req_time in requests if req_time > cutoff_minute)
    requests_last_hour = len(requests)

    # Check thresholds
    if requests_last_minute >= MAX_REQUESTS_PER_MINUTE:
        # Create breach alert
        await create_breach_alert(
            alert_type="rate_limit_exceeded",
            severity="medium",
            description=f"IP {ip_address} exceeded rate limit: {requests_last_minute} requests in 1 minute",
            ip_address=ip_address
        )
        return False, f"Rate limit exceeded: {requests_last_minute} requests in 1 minute (max: {MAX_REQUESTS_PER_MINUTE})"

    if requests_last_hour >= MAX_REQUESTS_PER_HOUR:
        await create_breach_alert(
            alert_type="rate_limit_exceeded",
            severity="high",
            description=f"IP {ip_address} exceeded hourly rate limit: {requests_last_hour} requests in 1 hour",
            ip_address=ip_address
        )
        return False, f"Rate limit exceeded: {requests_last_hour} requests in 1 hour (max: {MAX_REQUESTS_PER_HOUR})"

    # Add current request
    _ip_request_tracker[ip_address].append(now)

    return True, None


# ==================== AUTHENTICATION MONITORING ====================

async def track_auth_failure(ip_address: str, user_id: Optional[str] = None) -> bool:
    """
    Track failed authentication attempts

    Args:
        ip_address: Client IP address
        user_id: User ID if known

    Returns:
        True if threshold exceeded (suspicious), False otherwise
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=AUTH_FAILURE_WINDOW_MINUTES)

    # Get failures for this IP
    failures = _ip_auth_failures[ip_address]

    # Clean old entries
    failures = [failure_time for failure_time in failures if failure_time > cutoff]
    _ip_auth_failures[ip_address] = failures

    # Add current failure
    _ip_auth_failures[ip_address].append(now)

    # Check threshold
    if len(_ip_auth_failures[ip_address]) >= MAX_AUTH_FAILURES:
        # Create breach alert
        await create_breach_alert(
            alert_type="failed_authentication",
            severity="high",
            description=f"Multiple failed authentication attempts from IP {ip_address}: {len(failures)} failures in {AUTH_FAILURE_WINDOW_MINUTES} minutes",
            ip_address=ip_address,
            affected_users=[user_id] if user_id else None
        )
        return True

    return False


# ==================== UNUSUAL ACCESS DETECTION ====================

async def detect_unusual_access(user_id: str, ip_address: str) -> Optional[str]:
    """
    Detect unusual access patterns

    Checks for:
    - Access outside business hours
    - Access from new geographic locations
    - Unusual data access patterns

    Args:
        user_id: User ID
        ip_address: Client IP address

    Returns:
        Warning message if unusual, None otherwise
    """
    now = datetime.now(timezone.utc)
    current_hour = now.hour

    warnings = []

    # Check 1: Access outside business hours
    if current_hour < BUSINESS_HOURS_START or current_hour >= BUSINESS_HOURS_END:
        warnings.append(f"Access outside business hours (current hour: {current_hour})")

    # Check 2: Access from new IP (compare to user's history)
    async with async_session_factory() as session:
        # Get user's recent IPs
        result = await session.execute(
            select(AuditLog.ip_address)
            .filter_by(user_id=user_id)
            .filter(AuditLog.timestamp > now - timedelta(days=30))
            .distinct()
        )
        recent_ips = [row[0] for row in result.fetchall() if row[0]]

        if recent_ips and ip_address not in recent_ips:
            warnings.append(f"Access from new IP address: {ip_address}")

        # Check 3: Unusual volume of requests
        result = await session.execute(
            select(func.count(AuditLog.log_id))
            .filter_by(user_id=user_id)
            .filter(AuditLog.timestamp > now - timedelta(hours=1))
        )
        requests_last_hour = result.scalar()

        if requests_last_hour and requests_last_hour > 50:
            warnings.append(f"Unusual request volume: {requests_last_hour} requests in last hour")

    # Create breach alert if multiple warnings
    if len(warnings) >= 2:
        await create_breach_alert(
            alert_type="unusual_access",
            severity="medium",
            description=f"Unusual access pattern detected for user {user_id}: {'; '.join(warnings)}",
            ip_address=ip_address,
            affected_users=[user_id]
        )
        return "; ".join(warnings)

    return None


# ==================== BREACH ALERT MANAGEMENT ====================

async def create_breach_alert(
    alert_type: str,
    severity: str,
    description: str,
    ip_address: Optional[str] = None,
    affected_users: Optional[List[str]] = None
) -> str:
    """
    Create a breach alert

    Art. 33 requires notification to supervisory authority within 72 hours

    Args:
        alert_type: Type of alert ("rate_limit_exceeded", "failed_auth", "unusual_access", "data_leak")
        severity: Severity level ("low", "medium", "high", "critical")
        description: Human-readable description
        ip_address: IP address involved
        affected_users: List of affected user IDs

    Returns:
        alert_id: Unique identifier for the alert
    """
    alert_id = str(uuid.uuid4())

    async with async_session_factory() as session:
        alert = BreachAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            description=description,
            ip_address=ip_address,
            affected_users=affected_users,
            notified=False,
            resolved=False,
            detected_at=datetime.now(timezone.utc)
        )
        session.add(alert)
        await session.commit()

    # Log alert to console
    print(f"🚨 BREACH ALERT [{severity.upper()}]: {description}")

    # If high or critical, send immediate notification
    if severity in ["high", "critical"]:
        await _send_breach_notification(alert_id, alert_type, severity, description, affected_users)

    return alert_id


async def _send_breach_notification(
    alert_id: str,
    alert_type: str,
    severity: str,
    description: str,
    affected_users: Optional[List[str]] = None
):
    """
    Send breach notification (placeholder for email/SMS integration)

    In production, this should:
    - Send email to Data Protection Officer (DPO)
    - Send email to affected users (Art. 34)
    - Create incident report
    - Notify supervisory authority if required (Art. 33)

    Args:
        alert_id: Alert ID
        alert_type: Type of alert
        severity: Severity level
        description: Description
        affected_users: List of affected user IDs
    """
    # TODO: Integrate with email service (SendGrid, SES, etc.)
    # TODO: Integrate with incident management system

    print(f"\n{'='*80}")
    print(f"📧 BREACH NOTIFICATION REQUIRED")
    print(f"{'='*80}")
    print(f"Alert ID: {alert_id}")
    print(f"Type: {alert_type}")
    print(f"Severity: {severity.upper()}")
    print(f"Description: {description}")
    print(f"Affected Users: {len(affected_users) if affected_users else 0}")
    print(f"Detected: {datetime.now(timezone.utc).isoformat()}")
    print(f"\n⚠️  ACTION REQUIRED:")
    print(f"1. Notify Data Protection Officer (DPO)")
    print(f"2. Notify affected users (Art. 34)")
    print(f"3. If high-risk breach, notify supervisory authority within 72 hours (Art. 33)")
    print(f"{'='*80}\n")

    # Mark as notified
    async with async_session_factory() as session:
        result = await session.execute(select(BreachAlert).filter_by(alert_id=alert_id))
        alert = result.scalar_one_or_none()
        if alert:
            alert.notified = True
            alert.notification_timestamp = datetime.now(timezone.utc)
            await session.commit()


async def get_active_alerts(severity: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get all unresolved breach alerts

    Args:
        severity: Filter by severity (optional)

    Returns:
        List of active alerts
    """
    async with async_session_factory() as session:
        query = select(BreachAlert).filter_by(resolved=False)

        if severity:
            query = query.filter_by(severity=severity)

        query = query.order_by(BreachAlert.detected_at.desc())

        result = await session.execute(query)
        alerts = result.scalars().all()

        return [
            {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "description": alert.description,
                "ip_address": alert.ip_address,
                "affected_users": alert.affected_users,
                "notified": alert.notified,
                "notification_timestamp": alert.notification_timestamp.isoformat() if alert.notification_timestamp else None,
                "detected_at": alert.detected_at.isoformat() if alert.detected_at else None,
                "age_hours": (datetime.now(timezone.utc) - alert.detected_at).total_seconds() / 3600 if alert.detected_at else 0
            }
            for alert in alerts
        ]


async def resolve_alert(alert_id: str, resolution_notes: str) -> Dict[str, Any]:
    """
    Mark breach alert as resolved

    Args:
        alert_id: Alert ID
        resolution_notes: Notes about how the breach was resolved

    Returns:
        Updated alert data
    """
    async with async_session_factory() as session:
        result = await session.execute(select(BreachAlert).filter_by(alert_id=alert_id))
        alert = result.scalar_one_or_none()

        if not alert:
            return {
                "status": "error",
                "error": "Alert not found"
            }

        alert.resolved = True
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolution_notes = resolution_notes

        await session.commit()
        await session.refresh(alert)

        return {
            "status": "success",
            "alert_id": alert.alert_id,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
            "resolution_notes": alert.resolution_notes,
            "time_to_resolve_hours": (alert.resolved_at - alert.detected_at).total_seconds() / 3600 if alert.resolved_at and alert.detected_at else None
        }


# ==================== MONITORING AND REPORTING ====================

async def get_breach_statistics(days: int = 30) -> Dict[str, Any]:
    """
    Get breach detection statistics

    Args:
        days: Number of days to analyze

    Returns:
        Dictionary with breach statistics
    """
    async with async_session_factory() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Total alerts
        result = await session.execute(
            select(func.count(BreachAlert.alert_id))
            .filter(BreachAlert.detected_at > cutoff)
        )
        total_alerts = result.scalar()

        # Alerts by severity
        result = await session.execute(
            select(BreachAlert.severity, func.count(BreachAlert.alert_id))
            .filter(BreachAlert.detected_at > cutoff)
            .group_by(BreachAlert.severity)
        )
        alerts_by_severity = {row[0]: row[1] for row in result.fetchall()}

        # Alerts by type
        result = await session.execute(
            select(BreachAlert.alert_type, func.count(BreachAlert.alert_id))
            .filter(BreachAlert.detected_at > cutoff)
            .group_by(BreachAlert.alert_type)
        )
        alerts_by_type = {row[0]: row[1] for row in result.fetchall()}

        # Unresolved alerts
        result = await session.execute(
            select(func.count(BreachAlert.alert_id))
            .filter(BreachAlert.detected_at > cutoff)
            .filter_by(resolved=False)
        )
        unresolved_alerts = result.scalar()

        # Average resolution time
        result = await session.execute(
            select(BreachAlert)
            .filter(BreachAlert.detected_at > cutoff)
            .filter_by(resolved=True)
        )
        resolved_alerts_list = result.scalars().all()

        avg_resolution_hours = 0
        if resolved_alerts_list:
            total_resolution_time = sum(
                (alert.resolved_at - alert.detected_at).total_seconds() / 3600
                for alert in resolved_alerts_list
                if alert.resolved_at and alert.detected_at
            )
            avg_resolution_hours = total_resolution_time / len(resolved_alerts_list)

        return {
            "status": "success",
            "gdpr_article": "Article 33 - Breach Notification",
            "period_days": days,
            "statistics": {
                "total_alerts": total_alerts or 0,
                "unresolved_alerts": unresolved_alerts or 0,
                "resolved_alerts": (total_alerts or 0) - (unresolved_alerts or 0),
                "alerts_by_severity": alerts_by_severity,
                "alerts_by_type": alerts_by_type,
                "average_resolution_hours": round(avg_resolution_hours, 2)
            },
            "compliance_status": {
                "critical_alerts_unresolved": alerts_by_severity.get("critical", 0) if unresolved_alerts else 0,
                "alerts_older_than_72h": sum(
                    1 for alert in resolved_alerts_list
                    if (datetime.now(timezone.utc) - alert.detected_at).total_seconds() / 3600 > 72
                ) if resolved_alerts_list else 0,
                "notification_compliance": "COMPLIANT" if avg_resolution_hours < 72 else "AT_RISK"
            }
        }


async def check_72_hour_compliance() -> Dict[str, Any]:
    """
    Check compliance with 72-hour breach notification requirement (Art. 33)

    Returns:
        Dictionary with compliance status
    """
    async with async_session_factory() as session:
        cutoff_72h = datetime.now(timezone.utc) - timedelta(hours=72)

        # Get unresolved alerts older than 72 hours
        result = await session.execute(
            select(BreachAlert)
            .filter(BreachAlert.detected_at < cutoff_72h)
            .filter_by(resolved=False)
            .filter(BreachAlert.severity.in_(["high", "critical"]))
        )
        overdue_alerts = result.scalars().all()

        return {
            "status": "success",
            "gdpr_article": "Article 33 - 72-Hour Notification Requirement",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "compliance_status": "COMPLIANT" if not overdue_alerts else "NON_COMPLIANT",
            "overdue_alerts": [
                {
                    "alert_id": alert.alert_id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "description": alert.description,
                    "detected_at": alert.detected_at.isoformat() if alert.detected_at else None,
                    "hours_overdue": (datetime.now(timezone.utc) - alert.detected_at).total_seconds() / 3600 - 72 if alert.detected_at else 0
                }
                for alert in overdue_alerts
            ],
            "action_required": "Immediately notify supervisory authority for overdue high/critical alerts" if overdue_alerts else None
        }
