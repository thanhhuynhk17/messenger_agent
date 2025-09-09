"""
FastAPI webhook for Facebook Messenger – structured logging version.
"""
import os
import httpx
from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv

from utils.logger_setup import logger          # << NEW
from agent_client import LangGraphAgent

load_dotenv()

app = FastAPI()

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN      = os.getenv("VERIFY_TOKEN")
DEFAULT_AGENT_URL = os.getenv("AGENT_URL", "http://localhost:2024")
DEFAULT_ASSISTANT_ID = os.getenv("ASSISTANT_ID", "search_agent")

agent_client = LangGraphAgent(
    agent_url=DEFAULT_AGENT_URL,
    assistant_id=DEFAULT_ASSISTANT_ID
)

THREADS: dict[str, str] = {}


# --------------------------------------------------
# helper – Messenger Send API
# --------------------------------------------------
async def send_message(
    recipient_id: str,
    text: str,
    category: str = "id",
    message_type: str = "RESPONSE"
) -> httpx.Response:
    url = "https://graph.facebook.com/v23.0/me/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "recipient": {category: recipient_id},
        "message": {"text": text},
        "messaging_type": message_type
    }

    logger.debug("Outgoing FB message", extra={
        "recipient": recipient_id,
        "text": text
    })

    async with httpx.AsyncClient() as client:
        r = await client.post(url, params=params, json=payload)

    logger.info("FB send response", extra={
        "status": r.status_code,
        "body": r.text
    })
    return r


# --------------------------------------------------
# GET /webhook  (verification)
# --------------------------------------------------
@app.get("/webhook")
def verify_webhook(request: Request):
    logger.debug("Webhook verification attempt", extra={
        "query": dict(request.query_params)
    })

    mode      = request.query_params.get("hub.mode")
    token     = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("Webhook verification failed")
    return Response(content="Verification token mismatch", status_code=403)


# --------------------------------------------------
# POST /webhook  (events)
# --------------------------------------------------
PROCESSED_MIDS = set()
@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        data = await request.json()
    except Exception as exc:
        logger.exception("Malformed JSON received")
        return Response(content="BAD_REQUEST", status_code=400)

    logger.info("Webhook event received", extra={"payload": data})

    if data.get("object") != "page":
        return Response(content="EVENT_RECEIVED", media_type="text/plain")

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):

            # skip delivery / read
            if "delivery" in event or "read" in event:
                logger.debug("Skip delivery/read event")
                continue

            sender_id = event.get("sender", {}).get("id")
            if not sender_id:
                logger.debug("Missing sender id")
                continue

            if "message" not in event:
                continue

            message = event["message"]
            if message.get("is_echo"):
                logger.debug("Skip echo message")
                continue

            # duplicate guard (uncomment when needed)
            mid = message.get("mid")
            if mid in PROCESSED_MIDS:
                logger.warning("Duplicate mid dropped", extra={"mid": mid})
                continue
            PROCESSED_MIDS.add(mid)

            if "text" in message:
                user_msg = message["text"].strip()
                logger.info("User text message", extra={
                    "sender_id": sender_id,
                    "text": user_msg
                })

                await send_message(sender_id, "Khách iu vui lòng đợi chút ạ.")

                THREADS.setdefault(sender_id, None)
                try:
                    thread_id, ai_msg = await agent_client.chat(
                        user_msg, THREADS[sender_id]
                    )
                except Exception as exc:
                    logger.exception("Agent client error")
                    await send_message(
                        sender_id,
                        "Có lỗi xảy ra, bạn vui lòng thử lại nhé!"
                    )
                    continue

                THREADS[sender_id] = thread_id
                await send_message(sender_id, ai_msg.strip())

            else:
                logger.info("Unsupported message type", extra={
                    "sender_id": sender_id,
                    "message": message
                })
                await send_message(
                    sender_id,
                    "Mình chưa hỗ trợ gửi hình hay audio, chỉ có thể chat bằng văn bản thôi."
                )

    return Response(content="EVENT_RECEIVED", media_type="text/plain")