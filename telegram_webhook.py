# -*- coding: utf-8 -*-
import os, logging
from typing import Any, Dict
import requests
from flask import Blueprint, request, current_app, abort

try:
    from config import BOT_TOKEN, POST_CHANNEL_ID
except Exception:
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    POST_CHANNEL_ID = os.getenv("POST_CHANNEL_ID", "")

tg_webhook_bp = Blueprint("tg_webhook", __name__)

def send_message(chat_id: str, text: str) -> None:
    token = BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_id:
        current_app.logger.warning("No token or chat_id for send_message")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        if r.status_code != 200:
            current_app.logger.warning("sendMessage failed: %s %s", r.status_code, r.text[:200])
    except Exception as e:
        current_app.logger.exception("sendMessage exception: %s", e)

@tg_webhook_bp.post("/telegram/webhook")
def telegram_webhook():
    secret = os.getenv("WEBHOOK_SECRET", "")
    if secret:
        incoming = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if incoming != secret:
            abort(403)

    update: Dict[str, Any] = request.get_json(silent=True) or {}
    try:
        msg = update.get("message") or update.get("edited_message") or {}
        chat = msg.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        text = msg.get("text")
        if chat_id and text:
            send_message(chat_id, "✅ Бот подключён через webhook. Вы написали: " + text[:150])
    except Exception as e:
        current_app.logger.exception("Webhook minimal handler error: %s", e)
        return "", 200

    return "", 200

@tg_webhook_bp.get("/telegram/health")
def telegram_health():
    return {"ok": True}, 200