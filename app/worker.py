import asyncio
import logging
import uuid
from pythonjsonlogger import jsonlogger
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import NotificationModel
from app.queue import pop_from_queue

# Логгер для воркера
logger = logging.getLogger("notification_worker")
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(timestamp)s %(levelname)s %(name)s %(message)s %(trace_id)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)


async def process_notification(task: dict):
    """Имитация работы отправщика (Telegram/Email/Webhook)"""
    channel = task["channel"]
    recipient = task["recipient"]
    trace_id = task["trace_id"]
    task_id = task["task_id"]

    logger.info(
        f"Processing notification via {channel} to {recipient}",
        extra={"trace_id": trace_id, "task_id": task_id}
    )

    # Имитируем сетевую задержку отправки (например, запрос к Telegram API)
    await asyncio.sleep(1)

    # Имитация ошибки для демонстрации (если recipient == "error")
    if recipient == "error":
        raise Exception("Failed to send: External API returned 500 Internal Error")

    return True


async def run_worker():
    logger.info("Starting Notification Worker...", extra={"trace_id": "system"})

    while True:
        try:
            task = await pop_from_queue(timeout=2)
            if not task:
                continue

            task_id = task["task_id"]
            trace_id = task["trace_id"]

            async with AsyncSessionLocal() as db:
                # Находим запись в БД
                res = await db.execute(
                    select(NotificationModel).where(NotificationModel.id == uuid.UUID(task_id))
                )
                notification = res.scalars().first()

                if not notification:
                    logger.error(f"Notification {task_id} not found in DB", extra={"trace_id": trace_id})
                    continue

                try:
                    # Отправляем
                    await process_notification(task)

                    # Успех: меняем статус на SENT
                    notification.status = "SENT"
                    await db.commit()

                    logger.info("Notification successfully SENT", extra={"trace_id": trace_id, "task_id": task_id})

                except Exception as e:
                    # Ошибка: меняем статус на FAILED и сохраняем лог
                    notification.status = "FAILED"
                    notification.error_log = str(e)
                    await db.commit()

                    logger.error(
                        f"Notification FAILED: {str(e)}",
                        extra={"trace_id": trace_id, "task_id": task_id}
                    )

        except Exception as global_exc:
            logger.error(f"Worker loop error: {str(global_exc)}", extra={"trace_id": "system"})
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(run_worker())