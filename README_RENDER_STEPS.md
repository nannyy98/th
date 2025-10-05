# Быстрый запуск сайта + Telegram-бот (webhook) в одном сервисе Render

## 1) Скопируйте файлы в проект
Добавьте/замените в корне проекта:
- `telegram_webhook.py`
- `database.py` (с авто-миграциями)
- `config.py`
- `requirements.txt` (добавлен requests)

И подключите блюпринт в `app.py`:
```py
from telegram_webhook import tg_webhook_bp
app.register_blueprint(tg_webhook_bp)
```

## 2) Переменные окружения (Settings → Environment)
Обязательно:
```
TELEGRAM_BOT_TOKEN=8292684103:AAH0TKL-lCOaKVeppjtAdmsx0gdeMrGtjdQ
POST_CHANNEL_ID=-1002566537425
WEBHOOK_SECRET=aOB1J9y3P_F48n4WBbkBxcxfVvBo6DgZ
FLASK_SECRET_KEY=54b39727f7c24a7c5a62820fefb6e69e59562a4037a94cd71688555e62045320
DB_PATH=/var/data/shop_bot.db
ENVIRONMENT=production
```

## 3) Deploy
Нажмите **Manual Deploy → Clear build cache & deploy**.

## 4) Зарегистрировать webhook в Telegram (один раз)
Через curl:
```bash
curl -X POST "https://api.telegram.org/bot8292684103:AAH0TKL-lCOaKVeppjtAdmsx0gdeMrGtjdQ/setWebhook"       -d "url=https://<ВАШ-ДОМЕН>.onrender.com/telegram/webhook"       -d "secret_token=aOB1J9y3P_F48n4WBbkBxcxfVvBo6DgZ"
```
Замените `<ВАШ-ДОМЕН>` на ваш primary URL из Render.

## 5) Проверка
- Откройте `https://<ВАШ-ДОМЕН>.onrender.com/telegram/health` → `{"ok": true}`
- Напишите боту любое сообщение — он ответит: “Бот подключён через webhook”.

Готово!