import asyncio
import logging
import uuid
from pythonjsonlogger import jsonlogger
from sqlalchemy import select
# --- НОВЫЕ ИМПОРТЫ ---
from prometheus_client import start_http_server, Counter
# ---------------------

from app.database import AsyncSessionLocal
from app.models import NotificationModel
from app.redis_queue import pop_from_queue

# --- МЕТРИКИ PROMETHEUS ---
NOTIFICATIONS_SENT = Counter('notifications_sent_total', 'Total successfully sent notifications', ['channel'])
NOTIFICATIONS_FAILED = Counter('notifications_failed_total', 'Total failed notifications', ['channel'])
# --------------------------

# Логгер для воркера
logger = logging.getLogger("notification_worker")
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(timestamp)s %(levelname)s %(name)s %(message)s %(trace_id)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)


async def process_notification(task: dict):
    # ... (код без изменений) ...
    channel = task["channel"]
    recipient = task["recipient"]
    trace_id = task["trace_id"]
    task_id = task["task_id"]

    logger.info(
        f"Processing notification via {channel} to {recipient}",
        extra={"trace_id": trace_id, "task_id": task_id}
    )

    await asyncio.sleep(1)

    if recipient == "error":
        raise Exception("Failed to send: External API returned 500 Internal Error")

    return True


async def run_worker():
    logger.info("Starting Notification Worker...", extra={"trace_id": "system"})

    # Запускаем HTTP-сервер для отдачи метрик на порту 8001
    start_http_server(8001)
    logger.info("Metrics server started on port 8001")

    while True:
        try:
            task = await pop_from_queue(timeout=2)
            if not task:
                continue

            task_id = task["task_id"]
            trace_id = task["trace_id"]
            channel = task.get("channel", "unknown")

            async with AsyncSessionLocal() as db:
                res = await db.execute(
                    select(NotificationModel).where(NotificationModel.id == uuid.UUID(task_id))
                )
                notification = res.scalars().first()

                if not notification:
                    logger.error(f"Notification {task_id} not found in DB", extra={"trace_id": trace_id})
                    continue

                try:
                    await process_notification(task)

                    notification.status = "SENT"
                    await db.commit()

                    # Увеличиваем счетчик успешных
                    NOTIFICATIONS_SENT.labels(channel=channel).inc()

                    logger.info("Notification successfully SENT", extra={"trace_id": trace_id, "task_id": task_id})

                except Exception as e:
                    notification.status = "FAILED"
                    notification.error_log = str(e)
                    await db.commit()

                    # Увеличиваем счетчик ошибок
                    NOTIFICATIONS_FAILED.labels(channel=channel).inc()

                    logger.error(
                        f"Notification FAILED: {str(e)}",
                        extra={"trace_id": trace_id, "task_id": task_id}
                    )

        except Exception as global_exc:
            logger.error(f"Worker loop error: {str(global_exc)}", extra={"trace_id": "system"})
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(run_worker())