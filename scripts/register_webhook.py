#!/usr/bin/env python3
import os, sys, requests

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
    base = os.getenv("WEBHOOK_BASE") or (sys.argv[1] if len(sys.argv) > 1 else "")
    secret = os.getenv("WEBHOOK_SECRET") or (sys.argv[2] if len(sys.argv) > 2 else "")
    if not token or not base:
        print("Usage: TELEGRAM_BOT_TOKEN=... WEBHOOK_BASE=https://your.domain [WEBHOOK_SECRET=...] python scripts/register_webhook.py")
        sys.exit(2)
    url = f"https://api.telegram.org/bot{token}/setWebhook"
    payload = {"url": base.rstrip("/") + "/telegram/webhook"}
    if secret:
        payload["secret_token"] = secret
    r = requests.post(url, data=payload, timeout=15)
    print("Status:", r.status_code)
    print(r.text)

if __name__ == "__main__":
    main()