import time
import asyncio
#import aiohttp
import schemas
import random
async def generate_traffic():
    await asyncio.sleep(10)





if __name__ == "__main__":
    payload = {
      "channel": "",
      "message_type": "otp_code",
      "payload": {
        "code": "",
        "ttl_minutes": int
      },
      "recipient": "123456789",
      "source_service": ""
    }
    url = 'http://localhost:8000/api/v1/notifications/send'
   # while True:
    new_payload = payload.copy()
    incorrect_payload = payload.copy()
    new_payload["channel"] = random.choice(list(schemas.ChannelType)).value
    new_payload["source_service"] = random.choice(list(schemas.SourceService)).value
    new_payload["payload"]["code"] = random.randint(100000,600000)
    new_payload["payload"]["ttl_minutes"] = random.randint(1, 10)
    print(new_payload)
