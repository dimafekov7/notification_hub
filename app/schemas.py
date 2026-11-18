from enum import Enum
from typing import Any, Dict
from pydantic import BaseModel, Field


class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    EMAIL = "email"
    WEBHOOK = "webhook"


class SourceService(str, Enum):
    AUTH_SERVICE = "auth_service"
    BILLING_SERVICE = "billing_service"
    MONITORING = "monitoring"


class NotificationRequest(BaseModel):
    source_service: SourceService = Field(..., description="Сервис-отправитель")
    channel: ChannelType = Field(..., description="Канал доставки")
    recipient: str = Field(..., description="ID чата Telegram, Email или URL вебхука")
    message_type: str = Field(..., example="otp_code", description="Тип уведомления")
    payload: Dict[str, Any] = Field(..., description="Данные для шаблона или сообщения")

    class Config:
        json_schema_extra = {
            "example": {
                "source_service": "auth_service",
                "channel": "telegram",
                "recipient": "123456789",
                "message_type": "otp_code",
                "payload": {"code": "554123", "ttl_minutes": 5}
            }
        }


class NotificationResponse(BaseModel):
    status: str = "queued"
    task_id: str
    trace_id: str
    message: str = "Notification accepted for processing"