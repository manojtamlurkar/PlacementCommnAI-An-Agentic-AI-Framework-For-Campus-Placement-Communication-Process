import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.database.models import ActivityLog, RecruitmentDrive, EmailLog

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State Machine Map
# ---------------------------------------------------------------------------
WORKFLOW_MAP = {
    "INIT": "SEND_EMAIL",
    "CONTACTED": "WAIT_FOR_REPLY",
    "INFO_SHARED": "WAIT_FOR_CONFIRMATION",    # HR shared JD but not confirmed dates yet
    "DRIVE_CONFIRMED": "ASSIGN_SPOC",          # HR confirmed → assign SPOC
    "SPOC_ASSIGNED": "CREATE_TELEGRAM",         # SPOC assigned → create Telegram group
    "SPOC_HANDLING": "MONITOR_DRIVE",
    "SCHEDULE_RECEIVED": "SETUP_LOGISTICS",
    "LOGISTICS_CONFIRMED": "ASSIGN_SPOC",       # legacy fallback
    "APPROVED": "SPOC_HANDLING",
    "ACTIVE": "RUN_PROCESS",
    "COMPLETED": "DONE",
}

def get_next_step(status: str) -> str:
    return WORKFLOW_MAP.get(status.upper(), "UNKNOWN_STATUS")


# ---------------------------------------------------------------------------
# Orchestrator — silent observer + event logger
# ---------------------------------------------------------------------------
class Orchestrator:
    """
    Central observer for the entire recruitment pipeline.
    Logs all system events and can proactively flag stale drives.
    """

    @staticmethod
    def log_event(
        db: Session,
        actor: str,
        action: str,
        details: str,
        drive_id: int = None,
        company_id: int = None,
    ) -> ActivityLog:
        """
        Write a structured event to the activity_logs table.

        actor:   ORCHESTRATOR | SPOC | AGENT | SYSTEM | USER
        action:  e.g. EMAIL_SENT, SPOC_ASSIGNED, DRIVE_CONFIRMED, STALE_ALERT
        details: Human-readable description of what happened
        """
        try:
            entry = ActivityLog(
                drive_id=drive_id,
                company_id=company_id,
                actor=actor,
                action=action,
                details=details,
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            logger.info(f"[ORCHESTRATOR] {actor} | {action} | drive={drive_id} company={company_id}")
            return entry
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            db.rollback()
            return None

    @staticmethod
    def check_stale_drives(db: Session, stale_days: int = 3) -> list:
        """
        Scan for drives that have had no email activity for `stale_days` days.
        Logs a STALE_ALERT orchestrator event for each new stale drive.
        Returns list of stale drive IDs.
        """
        from backend.database.models import Company  # local import to avoid circular
        stale_ids = []
        threshold = datetime.utcnow() - timedelta(days=stale_days)

        try:
            active_drives = db.query(RecruitmentDrive).filter(
                RecruitmentDrive.status.notin_(["COMPLETED", "DONE"])
            ).all()

            for drive in active_drives:
                # Find company record for this drive
                company = db.query(Company).filter(
                    Company.company_name == drive.company_name
                ).first()
                if not company:
                    continue

                # Most recent email for this company
                latest_email = (
                    db.query(EmailLog)
                    .filter(EmailLog.company_id == company.id)
                    .order_by(EmailLog.timestamp.desc())
                    .first()
                )

                is_stale = (
                    latest_email is None or
                    (latest_email.timestamp and latest_email.timestamp < threshold)
                )

                if is_stale:
                    # Don't spam — only log once per stale window
                    recent_alert = (
                        db.query(ActivityLog)
                        .filter(
                            ActivityLog.drive_id == drive.id,
                            ActivityLog.action == "STALE_ALERT",
                            ActivityLog.timestamp >= threshold,
                        )
                        .first()
                    )
                    if not recent_alert:
                        Orchestrator.log_event(
                            db=db,
                            actor="ORCHESTRATOR",
                            action="STALE_ALERT",
                            details=f"Drive for {drive.company_name} has had no activity for {stale_days}+ days. Consider sending a follow-up.",
                            drive_id=drive.id,
                            company_id=company.id,
                        )
                        stale_ids.append(drive.id)
                        logger.warning(f"[ORCHESTRATOR] Stale drive: {drive.company_name} (id={drive.id})")

        except Exception as e:
            logger.error(f"check_stale_drives failed: {e}")

        return stale_ids


# Module-level singleton for convenience
orchestrator = Orchestrator()
