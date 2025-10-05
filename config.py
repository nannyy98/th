# Production-ready config with env overrides.
import os
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8292684103:AAH0TKL-lCOaKVeppjtAdmsx0gdeMrGtjdQ")
POST_CHANNEL_ID = os.getenv("POST_CHANNEL_ID", "-1002566537425")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "54b39727f7c24a7c5a62820fefb6e69e59562a4037a94cd71688555e62045320")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
DEBUG = ENVIRONMENT == "development"
DATABASE_CONFIG = {"path": os.getenv("DB_PATH") or os.getenv("DATABASE_PATH") or "shop_bot.db"}