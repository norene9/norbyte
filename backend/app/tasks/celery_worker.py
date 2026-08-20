import os
from celery import Celery
from celery.schedules import crontab
from croniter import croniter
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.repositories.connection_repository import ConnectionRepository
from app.repositories import DefinitionRepository
from app.services.sync_service import SyncService
from app.services.definition_service import DefinitionService
from app.models import Connection, SyncJob


# Broker URL: prefer REDIS_URL env var, fall back to local redis service
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("norbyte", broker=REDIS_URL)


@celery_app.task(name="norbyte.tasks.run_sync")
def run_sync_task(connection_id: int, job_id: int | None = None) -> dict:
    """Celery task wrapper that runs a sync for the given connection and updates the job.

    The task creates its own DB session and SyncService instance so it can run outside
    of the FastAPI request context.
    """
    db = SessionLocal()
    try:
        connection_repo = ConnectionRepository(db)
        definition_repo = DefinitionRepository(db)
        definition_service = DefinitionService(definition_repo)
        service = SyncService(db, connection_repo, definition_service)

        job = service.run_sync(connection_id, job_id=job_id)
        # Return a small summary for visibility in Celery results
        return {"job_id": job.id, "status": job.status, "records_processed": job.records_processed}
    finally:
        db.close()


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Run scheduler tick every minute
    sender.add_periodic_task(60.0, scheduler_tick.s(), name="scheduler-tick-every-minute")


@celery_app.task(name="norbyte.tasks.scheduler_tick")
def scheduler_tick():
    """Periodic scheduler that enqueues connection syncs based on `Connection.schedule`.

    Supports simple enums: 'manual' (skip), 'hourly', 'daily'
    Or a cron expression (evaluated with croniter).
    """
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        connections = db.query(Connection).all()
        for conn in connections:
            sched = (conn.schedule or "").strip()
            if not sched or sched.lower() in ("manual", "none"):
                continue

            last_ts = None
            if conn.last_scheduled_at:
                try:
                    last_ts = datetime.fromisoformat(conn.last_scheduled_at)
                except Exception:
                    last_ts = None

            due = False

            # Enum schedules
            if sched.lower() == "hourly":
                if not last_ts or (now - last_ts).total_seconds() >= 3600:
                    due = True
            elif sched.lower() == "daily":
                if not last_ts or (now - last_ts).total_seconds() >= 86400:
                    due = True
            else:
                # Treat as cron expression
                try:
                    base = last_ts or (now - croniter(sched, now).get_prev(datetime))
                    it = croniter(sched, base)
                    next_occurrence = it.get_next(datetime)
                    if next_occurrence <= now:
                        due = True
                except Exception:
                    # invalid cron — skip
                    continue

            if due:
                # create queued job and enqueue
                job = SyncJob(connection_id=conn.id, status="queued", started_at=None, records_processed=0, logs="")
                db.add(job)
                # update last_scheduled_at to now to avoid double scheduling
                conn.last_scheduled_at = now.isoformat()
                db.add(conn)
                db.commit()
                db.refresh(job)
                try:
                    run_sync_task.delay(conn.id, job.id)
                except Exception:
                    # fallback to synchronous call
                    connection_repo = ConnectionRepository(db)
                    definition_repo = DefinitionRepository(db)
                    definition_service = DefinitionService(definition_repo)
                    service = SyncService(db, connection_repo, definition_service)
                    service.run_sync(conn.id, job_id=job.id)
    finally:
        db.close()
