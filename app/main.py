import uuid
import logging
from fastapi import FastAPI, Request, Depends
from pythonjsonlogger import jsonlogger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.redis_queue import push_to_queue
from prometheus_fastapi_instrumentator import Instrumentator
from app.database import engine, get_db
from app.models import Base, NotificationModel, ServiceModel, ChannelModel
from app.schemas import NotificationRequest, NotificationResponse


logger = logging.getLogger("notification_hub")
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(timestamp)s %(levelname)s %(name)s %(message)s %(trace_id)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

app = FastAPI(title="Notification Hub API", version="1.0.0")
Instrumentator().instrument(app).expose(app)

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    return response


@app.post("/api/v1/notifications/send", response_model=NotificationResponse)
async def send_notification(
        payload: NotificationRequest,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    trace_id = request.state.trace_id

    service = await get_or_create_service(db, payload.source_service.value)
    channel = await get_or_create_channel(db, payload.channel.value)

    notification = NotificationModel(
        service_id=service.id,
        channel_id=channel.id,
        recipient=payload.recipient,
        message_type=payload.message_type,
        payload=payload.payload,
        status="PENDING",
        trace_id=trace_id
    )

    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    # NEW: Пушим задачу в очередь Redis
    task_data = {
        "task_id": str(notification.id),
        "channel": payload.channel.value,
        "recipient": payload.recipient,
        "payload": payload.payload,
        "trace_id": trace_id
    }
    await push_to_queue(task_data)

    logger.info(
        "Notification created and pushed to Redis",
        extra={
            "trace_id": trace_id,
            "task_id": str(notification.id),
            "source": payload.source_service,
            "channel": payload.channel
        }
    )

    return NotificationResponse(
        status="queued",
        task_id=str(notification.id),
        trace_id=trace_id,
        message="Notification stored in DB and pushed to queue"
    )


async def get_or_create_service(db: AsyncSession, name: str) -> ServiceModel:
    res = await db.execute(select(ServiceModel).where(ServiceModel.name == name))
    service = res.scalars().first()
    if not service:
        service = ServiceModel(name=name)
        db.add(service)
        await db.commit()
        await db.refresh(service)
    return service


async def get_or_create_channel(db: AsyncSession, name: str) -> ChannelModel:
    res = await db.execute(select(ChannelModel).where(ChannelModel.name == name))
    channel = res.scalars().first()
    if not channel:
        channel = ChannelModel(name=name)
        db.add(channel)
        await db.commit()
        await db.refresh(channel)
    return channel