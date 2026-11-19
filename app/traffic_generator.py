import asyncio
import random
import httpx
import schemas


async def generate_traffic():
    url = 'http://localhost:8000/api/v1/notifications/send'

    async with httpx.AsyncClient() as client:
        while True:
            # Выбираем сценарий:
            # 0-70: Успешный запрос
            # 70-85: Ошибка валидации (422)
            # 85-95: Ошибка воркера (FAILED)
            # 95-100: Неверный URL (404)
            dice = random.randint(1, 100)

            try:
                if dice <= 70:
                    # 1. ХОРОШИЙ ЗАПРОС
                    payload = {
                        "channel": random.choice(list(schemas.ChannelType)).value,
                        "message_type": "otp_code",
                        "payload": {
                            "code": str(random.randint(100000, 600000)),
                            "ttl_minutes": random.randint(1, 10)
                        },
                        "recipient": "123456789",
                        "source_service": random.choice(list(schemas.SourceService)).value
                    }
                    response = await client.post(url, json=payload)
                    print(f"[{response.status_code}] OK: Sent to {payload['channel']}")

                elif dice <= 85:
                    # 2. ПЛОХОЙ ЗАПРОС (Ошибка валидации 422)
                    # Забыли передать поле recipient, или передали неверный enum
                    bad_payload = {
                        "channel": "sms",  # Такого канала нет в enum, будет 422
                        "message_type": "otp_code",
                        "payload": {"code": "123", "ttl_minutes": 5},
                        "recipient": "123456789",
                        "source_service": "auth_service"
                    }
                    response = await client.post(url, json=bad_payload)
                    print(f"[{response.status_code}] BAD REQUEST: Validation error")

                elif dice <= 95:
                    # 3. ОШИБКА ВОРКЕРА (API вернет 200, но воркер упадет с FAILED)
                    payload = {
                        "channel": "telegram",
                        "message_type": "otp_code",
                        "payload": {"code": "999999", "ttl_minutes": 5},
                        "recipient": "error",  # Специальный маркер для воркера
                        "source_service": "auth_service"
                    }
                    response = await client.post(url, json=payload)
                    print(f"[{response.status_code}] OK: Sent, but worker will fail (recipient='error')")

                else:
                    # 4. НЕВЕРНЫЙ URL (Ошибка 404)
                    bad_url = 'http://localhost:8000/api/v1/notifications/unknown'
                    response = await client.post(bad_url, json={})
                    print(f"[{response.status_code}] NOT FOUND")

            except Exception as e:
                print(f"Error: {e}")

            # Пауза между запросами (0.2 - 0.8 сек)
            await asyncio.sleep(random.uniform(0.2, 0.8))


if __name__ == "__main__":
    asyncio.run(generate_traffic())