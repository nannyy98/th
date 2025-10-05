# 🤖 Пошаговая настройка Telegram бота

## 1. Создание бота через BotFather

1. **Найдите @BotFather** в Telegram
2. **Отправьте команду** `/newbot`
3. **Введите название** бота (например: "My Shop Bot")
4. **Введите username** бота (должен заканчиваться на "bot", например: "myshop_bot")
5. **Скопируйте токен** - выглядит примерно так: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

## 2. Настройка токена в коде

### Способ 1: Файл .env (РЕКОМЕНДУЕТСЯ)

1. **Скопируйте файл настроек:**
```bash
cp .env.example .env
```

2. **Отредактируйте .env файл:**
```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
BOT_NAME=My Shop Bot

# Admin Configuration  
ADMIN_TELEGRAM_ID=123456789
ADMIN_NAME=Ваше Имя

# Environment
ENVIRONMENT=production
```

3. **Запустите бота:**
```bash
python main.py
```

### Способ 1: Переменная окружения (РЕКОМЕНДУЕТСЯ)

**Linux/Mac:**
```bash
export TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
python main.py
```

**Windows (Command Prompt):**
```cmd
set TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
python main.py
```

**Windows (PowerShell):**
```powershell
$env:TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
python main.py
```

### Способ 2: Прямо в коде (для тестирования)

Откройте `main.py` и найдите строки:
```python
# Способ 2: Прямо в коде (только для тестирования!)
# token = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
```

Раскомментируйте и замените на ваш токен:
```python
# Способ 2: Прямо в коде (только для тестирования!)
token = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
```

## 3. Пример реального токена

Токен выглядит примерно так:
```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890
```

**Структура токена:**
- `1234567890` - ID бота
- `:` - разделитель
- `ABCdefGHIjklMNOpqrsTUVwxyz-1234567890` - секретная часть

## 4. Проверка работы

После настройки токена:
1. Запустите `python main.py`
2. Найдите вашего бота в Telegram
3. Отправьте `/start`
4. Должно появиться приветственное сообщение

## 5. Безопасность

⚠️ **ВАЖНО:**
- **НЕ публикуйте** токен в открытых репозиториях
- **НЕ делитесь** токеном с другими
- **Используйте переменные окружения** в продакшене
- **Регенерируйте токен** если он скомпрометирован

## 6. Настройка бота через BotFather

После создания бота настройте его:

```
/setdescription - Интернет-магазин с доставкой
/setabouttext - Покупайте товары прямо в Telegram!
/setuserpic - Загрузите аватар бота
/setcommands - Настройте команды:

start - Начать работу
help - Справка
catalog - Каталог товаров
cart - Корзина
orders - Мои заказы
profile - Профиль
search - Поиск товаров
track - Отследить заказ
```

## 7. Первый запуск

1. **Запустите бота**: `python main.py`
2. **Админ создается автоматически** из .env файла
3. **Найдите в Telegram** по username
4. **Отправьте** `/start`
5. **Пройдите регистрацию**
6. **Используйте** `/admin` для входа в админ-панель

### Как узнать свой Telegram ID:
1. Напишите боту [@userinfobot](https://t.me/userinfobot)
2. Скопируйте ваш ID
3. Добавьте в .env файл: `ADMIN_TELEGRAM_ID=ваш_id`

## 8. Тестирование функций

После настройки протестируйте:
- ✅ Регистрацию нового пользователя
- ✅ Просмотр каталога
- ✅ Добавление в корзину
- ✅ Оформление заказа
- ✅ Админ-панель (`/admin`)
- ✅ Статистику и отчеты

🎉 **Готово!** Ваш интернет-магазин готов к работе!