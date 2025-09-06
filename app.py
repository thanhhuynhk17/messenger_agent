# app.py
import os
import httpx                      # pip install httpx
from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv
from agent_client import LangGraphAgent
import asyncio

load_dotenv()

app = FastAPI()

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN      = os.getenv("VERIFY_TOKEN")      # must match FB dashboard

DEFAULT_AGENT_URL   = os.getenv("AGENT_URL", "http://localhost:2024")
DEFAULT_ASSISTANT_ID = os.getenv("ASSISTANT_ID", "search_agent")
agent_client = LangGraphAgent(
    agent_url=DEFAULT_AGENT_URL,
    assistant_id=DEFAULT_ASSISTANT_ID
)

# --------------------------------------------------
# per-user thread store                             # NEW
# --------------------------------------------------
THREADS: dict[str, str] = {}


# --------------------------------------------------
# async helper that talks to the Messenger Send API
# --------------------------------------------------
async def send_message(
    recipient_id: str,
    text: str,
    category: str = "id",
    message_type: str = "RESPONSE"
):
    url = "https://graph.facebook.com/v21.0/me/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "recipient": {category: recipient_id},
        "message": {"text": text},
        "messaging_type": message_type
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(url, params=params, json=payload)
    print("Send Message Response:", r.status_code, r.text)
    return r

# --------------------------------------------------
# Webhook verification (GET)
# --------------------------------------------------
@app.get("/webhook")
def verify_webhook(request: Request):
    print("PAGE_ACCESS_TOKEN", PAGE_ACCESS_TOKEN[-3:])
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Verification token mismatch", status_code=403)
# --------------------------------------------------
# Webhook events (POST)
# --------------------------------------------------
# set lưu mid đã xử lý
PROCESSED_MIDS = set()

@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    print("Webhook post event:", data)

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):

                # ❌ bỏ qua delivery & read ngay từ đầu
                print("Check: delivery or read")
                if "delivery" in event or "read" in event:
                    print("Skip: delivery or read")
                    continue
                print("Pass: delivery or read")

                sender_id = event.get("sender", {}).get("id")
                if not sender_id:
                    continue

                # ✅ xử lý message
                if "message" in event:
                    message = event["message"]

                    # ignore echoes
                    if message.get("is_echo"):
                        continue

                    mid = message.get("mid")
                    if mid in PROCESSED_MIDS:
                        print(f"⚠️ Bỏ qua duplicate mid: {mid}")
                        continue
                    PROCESSED_MIDS.add(mid)

                    if "text" in message:
                        user_msg = message["text"].strip()
                        print("Bạn vừa nói:", user_msg)
                        await send_message(sender_id, "Khách iu vui lòng đợi chút ạ.")

                        if sender_id not in THREADS:
                            THREADS[sender_id] = None

                        thread_id, ai_msg = await agent_client.chat(
                            user_msg, THREADS[sender_id]
                        )
                        THREADS[sender_id] = thread_id
                        await send_message(sender_id, ai_msg.strip())
                    else:
                        await send_message(
                            sender_id,
                            "Mình chưa hỗ trợ gửi hình hay audio, chỉ có thể chat bằng văn bản thôi."
                        )

    return Response(content="EVENT_RECEIVED", media_type="text/plain")
