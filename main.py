"""
Главный файл запуска телеграм-бота интернет-магазина
"""
import logging

import json
import urllib.request
import urllib.parse
import os
import time
import signal
import sys
import threading
from database import DatabaseManager
from handlers import MessageHandler
from notifications import NotificationManager
from utils import format_date
from payments import PaymentProcessor
from logistics import LogisticsManager
from promotions import PromotionManager
from crm import CRMManager
from logger import logger
from health_check import HealthMonitor
from database_backup import DatabaseBackup
from scheduled_posts import ScheduledPostsManager
from config import BOT_CONFIG, BOT_TOKEN

# Импорты с обработкой ошибок
from datetime import datetime
try:
    from admin import AdminHandler
except ImportError:
    AdminHandler = None
    logging.info("⚠️ AdminHandler не найден, админ-функции недоступны")

try:
    from security import SecurityManager
except ImportError:
    SecurityManager = None
    logging.info("⚠️ SecurityManager не найден, функции безопасности ограничены")

try:
    from webhooks import WebhookManager
except ImportError:
    WebhookManager = None
    logging.info("⚠️ WebhookManager не найден, webhook'и недоступны")

try:
    from analytics import AnalyticsManager
except ImportError:
    AnalyticsManager = None
    logging.info("⚠️ AnalyticsManager не найден, аналитика недоступна")

try:
    from financial_reports import FinancialReportsManager
except ImportError:
    FinancialReportsManager = None
    logging.info("⚠️ FinancialReportsManager не найден, финансовые отчеты недоступны")

try:
    from inventory_management import InventoryManager
except ImportError:
    InventoryManager = None
    logging.info("⚠️ InventoryManager не найден, управление складом недоступно")

try:
    from ai_features import AIRecommendationEngine, ChatbotSupport, SmartNotificationAI
except ImportError:
    AIRecommendationEngine = None
    ChatbotSupport = None
    SmartNotificationAI = None
    logging.info("⚠️ AI модули не найдены, AI функции недоступны")

try:
    from marketing_automation import MarketingAutomationManager
except ImportError:
    MarketingAutomationManager = None
    logging.info("⚠️ MarketingAutomationManager не найден, автоматизация недоступна")

class TelegramShopBot:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        self.running = True
        self.error_count = 0
        self.max_errors = 10
        self.data_cache = {}
        self.last_data_reload = time.time()
        
        # Инициализация компонентов
        self.db = DatabaseManager()
        self.setup_admin_from_env()
        self.backup_manager = DatabaseBackup(self.db.db_path)
        self.message_handler = MessageHandler(self, self.db)
        self.notification_manager = NotificationManager(self, self.db)
        self.payment_processor = PaymentProcessor()
        
        # Система мониторинга
        self.health_monitor = HealthMonitor(self.db, self)
        
        # Инициализация админ-панели
        if AdminHandler:
            self.admin_handler = AdminHandler(self, self.db)
        else:
            self.admin_handler = None
        
        # Инициализация бизнес-модулей
        self.logistics_manager = LogisticsManager(self.db)
        self.promotion_manager = PromotionManager(self.db)
        self.crm_manager = CRMManager(self.db)
        
        # Связываем компоненты
        self.message_handler.notification_manager = self.notification_manager
        self.admin_handler.notification_manager = self.notification_manager
        self.message_handler.payment_processor = self.payment_processor
        
        # Инициализируем безопасность
        if SecurityManager:
            self.security_manager = SecurityManager(self.db)
        else:
            self.security_manager = None
        
        # Инициализируем webhook'и
        if WebhookManager and self.security_manager:
            self.webhook_manager = WebhookManager(self, self.db, self.security_manager)
        else:
            self.webhook_manager = None
        
        # Запускаем аналитические отчеты
        if AnalyticsManager:
            self.analytics = AnalyticsManager(self.db)
            self.analytics.schedule_analytics_reports()
        else:
            self.analytics = None
        
        # Инициализируем финансовую отчетность
        if FinancialReportsManager:
            self.financial_reports = FinancialReportsManager(self.db)
        else:
            self.financial_reports = None
        
        # Инициализируем управление складом
        if InventoryManager:
            self.inventory_manager = InventoryManager(self.db)
            self.inventory_manager.bot = self  # Добавляем ссылку на бота
        else:
            self.inventory_manager = None
        
        # Инициализируем AI функции
        if AIRecommendationEngine:
            self.ai_recommendations = AIRecommendationEngine(self.db)
        else:
            self.ai_recommendations = None
            
        if ChatbotSupport:
            self.chatbot_support = ChatbotSupport(self.db)
        else:
            self.chatbot_support = None
            
        if SmartNotificationAI:
            self.smart_notifications = SmartNotificationAI(self.db)
        else:
            self.smart_notifications = None
        
        # Инициализируем маркетинговую автоматизацию
        if MarketingAutomationManager:
            self.marketing_automation = MarketingAutomationManager(self.db, self.notification_manager)
        else:
            self.marketing_automation = None
        
        # Инициализируем систему автоматических постов
        try:
            from scheduled_posts import ScheduledPostsManager
            self.scheduled_posts = ScheduledPostsManager(self, self.db)
            # Передаем ссылку на бота в менеджер постов
            self.scheduled_posts.bot = self
            logger.info("✅ Система автоматических постов инициализирована")
        except Exception as e:
            logger.warning(f"⚠️ Автопосты недоступны (модуль schedule не установлен): {e}")
            self.scheduled_posts = None
        
        # Запускаем автоматические проверки склада ПОСЛЕ инициализации всех компонентов
        self.schedule_inventory_checks()
        
        # Инициализируем автоматизацию маркетинга только если модуль доступен
        if self.marketing_automation:
            self.setup_default_automation_rules()
        
        # Настройка обработчиков сигналов
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Запускаем проверку обновлений данных
        self.start_data_sync_monitor()
        
        logger.info("✅ Бот инициализирован успешно")
    
    def start_data_sync_monitor(self):
        """Запуск мониторинга обновлений данных"""
        def sync_worker():
            while self.running:
                try:
                    self.check_for_data_updates()
                    time.sleep(5)  # Проверяем каждые 5 секунд
                except Exception as e:
                    logger.error(f"Ошибка синхронизации данных: {e}")
                    time.sleep(30)
        
        sync_thread = threading.Thread(target=sync_worker, daemon=True)
        sync_thread.start()
        logger.info("Мониторинг синхронизации данных запущен")
    
    def check_for_data_updates(self):
        """Проверка обновлений данных"""
        # Проверяем обычный флаг обновления
        update_flag_file = 'data_update_flag.txt'
        force_reload_flag = 'force_reload_flag.txt'
        
        # Проверяем принудительную перезагрузку
        if os.path.exists(force_reload_flag):
            try:
                logger.info("🔄 ПРИНУДИТЕЛЬНАЯ ПЕРЕЗАГРУЗКА данных...")
                self.full_data_reload()
                os.remove(force_reload_flag)
                logger.info("✅ Принудительная перезагрузка завершена")
            except Exception as e:
                logger.error(f"Ошибка принудительной перезагрузки: {e}")
                try:
                    os.remove(force_reload_flag)
                except Exception:
                    pass
        
        # Проверяем обычное обновление
        elif os.path.exists(update_flag_file):
            try:
                # Читаем время последнего обновления
                with open(update_flag_file, 'r') as f:
                    update_time_str = f.read().strip()
                
                update_time = float(update_time_str)
                
                # Если обновление новее нашего последнего обновления
                if update_time > self.last_data_reload:
                    logger.info("🔄 Обнаружено обновление данных, перезагружаем...")
                    self.reload_data_cache()
                    self.last_data_reload = update_time
                    
                    # Удаляем флаг
                    os.remove(update_flag_file)
                    logger.info("✅ Данные обновлены в боте")
                    
            except Exception as e:
                logger.error(f"Ошибка обработки флага обновления: {e}")
                # Удаляем поврежденный флаг
                try:
                    os.remove(update_flag_file)
                except Exception:
                    pass
    
    def full_data_reload(self):
        """Полная перезагрузка всех данных и компонентов"""
        try:
            # Перезагружаем базу данных
            self.db = DatabaseManager()
            
            # Перезагружаем кэш
            self.reload_data_cache()
            
            # Перезагружаем автопосты
            if hasattr(self, 'scheduled_posts') and self.scheduled_posts:
                self.scheduled_posts.load_schedule_from_database()
            
            # Перезагружаем правила автоматизации
            if hasattr(self, 'marketing_automation') and self.marketing_automation:
                self.setup_default_automation_rules()
            
            logger.info("✅ Полная перезагрузка данных завершена")
            
        except Exception as e:
            logger.error(f"Ошибка полной перезагрузки: {e}")
    
    def reload_data_cache(self):
        """Перезагрузка кэша данных"""
        try:
            # Очищаем кэш
            self.data_cache.clear()
            
            # Перезагружаем категории
            self.data_cache['categories'] = self.db.get_categories()
            
            # Перезагружаем товары
            self.data_cache['products'] = self.db.execute_query(
                'SELECT * FROM products WHERE is_active = 1 ORDER BY name'
            )
            
            # Перезагружаем автопосты если есть модуль
            if hasattr(self, 'scheduled_posts') and self.scheduled_posts:
                self.scheduled_posts.load_schedule_from_database()
            
            # Уведомляем админов об обновлении
            self.notify_admins_about_update()
            
        except Exception as e:
            logger.error(f"Ошибка перезагрузки данных: {e}")
    
    def notify_admins_about_update(self):
        """Уведомление админов об обновлении данных"""
        try:
            admins = self.db.execute_query('SELECT telegram_id FROM users WHERE is_admin = 1')
            
            update_message = "🔄 <b>Данные обновлены!</b>\n\n"
            update_message += "✅ Каталог товаров синхронизирован\n"
            update_message += "✅ Категории обновлены\n"
            update_message += "✅ Автопосты перезагружены\n\n"
            update_message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            
            for admin in admins:
                try:
                    self.send_message(admin[0], update_message)
                except Exception as e:
                    logger.error(f"Ошибка уведомления админа {admin[0]}: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка уведомления админов: {e}")
    
    def trigger_data_update(self):
        """Принудительное обновление данных"""
        update_flag_file = 'data_update_flag.txt'
        try:
            with open(update_flag_file, 'w') as f:
                f.write(str(time.time()))
            logger.info("Флаг обновления данных установлен")
        except Exception as e:
            logger.error(f"Ошибка установки флага обновления: {e}")
    
    def setup_admin_from_env(self):
        """Настройка админа из переменных окружения"""
        from config import BOT_CONFIG
        
        admin_telegram_id = BOT_CONFIG.get('admin_telegram_id')
        admin_name = BOT_CONFIG.get('admin_name', 'Admin')
        
        if admin_telegram_id:
            try:
                admin_telegram_id = int(admin_telegram_id)
                
                # Проверяем существует ли админ
                existing_admin = self.db.execute_query(
                    'SELECT id, is_admin FROM users WHERE telegram_id = ?',
                    (admin_telegram_id,)
                )
                
                if existing_admin:
                    # Обновляем права админа если нужно
                    if existing_admin[0][1] != 1:
                        self.db.execute_query(
                            'UPDATE users SET is_admin = 1 WHERE telegram_id = ?',
                            (admin_telegram_id,)
                        )
                        logger.info(f"✅ Права админа обновлены для {admin_name}")
                    else:
                        logger.info(f"✅ Админ уже существует: {admin_name}")
                else:
                    # Создаем нового админа
                    self.db.execute_query('''
                        INSERT INTO users (telegram_id, name, is_admin, language, created_at)
                        VALUES (?, ?, 1, 'ru', CURRENT_TIMESTAMP)
                    ''', (admin_telegram_id, admin_name))
                    logger.info(f"✅ Новый админ создан: {admin_name} (ID: {admin_telegram_id})")
                    
            except ValueError:
                logger.error(f"❌ Неверный ADMIN_TELEGRAM_ID: {admin_telegram_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка создания админа: {e}")
    
    def signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown"""
        logger.info(f"Получен сигнал {signum}, завершение работы...")
        self.running = False
        sys.exit(0)
    
    def schedule_inventory_checks(self):
        """Планирование проверок склада"""
        if not hasattr(self, 'inventory_manager') or not self.inventory_manager:
            return
            
        import threading
        import time
        
        def inventory_worker():
            while True:
                try:
                    # Проверяем каждые 6 часов
                    if hasattr(self, 'inventory_manager') and self.inventory_manager:
                        self.inventory_manager.check_reorder_alerts()
                        self.inventory_manager.process_automatic_reorders()
                    time.sleep(21600)  # 6 часов
                except Exception as e:
                    logging.info(f"Ошибка проверки склада: {e}")
                    time.sleep(3600)  # Повтор через час при ошибке
        
        inventory_thread = threading.Thread(target=inventory_worker, daemon=True)
        inventory_thread.start()
    
    def setup_default_automation_rules(self):
        """Настройка базовых правил автоматизации"""
        try:
            if not self.marketing_automation:
                return
            
            # Правило для брошенных корзин
            self.marketing_automation.create_automation_rule(
                "Брошенные корзины 24ч",
                "cart_abandonment",
                {"hours_since_last_activity": 24, "min_cart_value": 20},
                [{"type": "send_notification", "target_audience": "abandoned_cart", 
                  "message_template": "🛒 {name}, не забудьте о товарах в корзине!"}]
            )
            
            # Правило для первого заказа
            self.marketing_automation.create_automation_rule(
                "Первый заказ - благодарность",
                "customer_milestone",
                {"milestone_type": "first_order"},
                [{"type": "send_notification", "target_audience": "first_time_buyers",
                  "message_template": "🎉 Спасибо за первый заказ, {name}! Ждите следующих предложений!"}]
            )
            
            # Правило для VIP клиентов
            self.marketing_automation.create_automation_rule(
                "VIP статус достигнут",
                "customer_milestone", 
                {"milestone_type": "spending_threshold", "spending_amount": 500},
                [{"type": "send_personalized_offer", "target_segment": "champions"}]
            )
        except Exception as e:
            logging.info(f"⚠️ Ошибка настройки автоматизации: {e}")
    
    def send_message(self, chat_id, text, reply_markup=None):
        """Отправка сообщения"""
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        try:
            data_encoded = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_encoded, method='POST')
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                if not result.get('ok'):
                    logging.info(f"Ошибка отправки сообщения: {result}")
                return result
        except Exception as e:
            logging.info(f"Ошибка отправки сообщения: {e}")
            return None
    
    def send_photo(self, chat_id, photo_url, caption="", reply_markup=None):
        """Отправка фото"""
        url = f"{self.base_url}/sendPhoto"
        data = {
            'chat_id': chat_id,
            'photo': photo_url,
            'caption': caption,
            'parse_mode': 'HTML'
        }
        
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        try:
            data_encoded = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_encoded, method='POST')
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                if not result.get('ok'):
                    logging.info(f"Ошибка отправки фото: {result}")
                return result
        except Exception as e:
            logging.info(f"Ошибка отправки фото: {e}")
            return None
    
    def get_updates(self):
        """Получение обновлений"""
        url = f"{self.base_url}/getUpdates"
        params = {'offset': self.offset, 'timeout': 30}
        
        try:
            url_with_params = f"{url}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(url_with_params) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except Exception as e:
            logging.info(f"Ошибка получения обновлений: {e}")
            return None
    
    def run(self):
        """Запуск бота"""
        logger.info("🛍 Телеграм-бот интернет-магазина запущен!")
        logger.info("📱 Ожидание сообщений...")
        logger.info("Нажмите Ctrl+C для остановки")
        
        try:
            while self.running:
                updates = self.get_updates()
                
                if updates and updates.get('ok'):
                    self.error_count = 0  # Сбрасываем счетчик ошибок при успехе
                    
                    for update in updates['result']:
                        self.offset = update['update_id'] + 1
                        
                        try:
                            self.health_monitor.increment_messages()
                            
                            if 'message' in update:
                                message = update['message']
                                text = message.get('text', '')
                                telegram_id = message['from']['id']
                                
                                # Логируем сообщение
                                logger.info(f"Сообщение от {telegram_id}: {text[:50]}...")
                                
                                # Проверяем админ команды
                                if self.admin_handler and (text.startswith('/admin') or text in ['📊 Статистика', '📦 Заказы', '🛠 Товары', '👥 Пользователи', '🔙 Пользовательский режим']):
                                    self.admin_handler.handle_admin_command(message)
                                elif self.admin_handler and text in ['📈 Аналитика', '🛡 Безопасность', '💰 Финансы', '📦 Склад', '🤖 AI', '🎯 Автоматизация', '👥 CRM', '📢 Рассылка']:
                                    self.admin_handler.handle_admin_command(message)
                                elif self.admin_handler and text.startswith('/admin_order_'):
                                    self.admin_handler.handle_order_management(message)
                                elif self.admin_handler and (text.startswith('/edit_product_') or text.startswith('/delete_product_')):
                                    self.admin_handler.handle_product_commands(message)
                                elif self.admin_handler and hasattr(self.admin_handler, 'admin_states') and self.admin_handler.admin_states.get(telegram_id):
                                    state = self.admin_handler.admin_states.get(telegram_id, '')
                                    if state.startswith('adding_product_'):
                                        self.admin_handler.handle_add_product_process(message)
                                    elif state.startswith('creating_broadcast_'):
                                        self.admin_handler.handle_broadcast_creation(message)
                                elif text == '/notifications':
                                    self.show_user_notifications(message)
                                else:
                                    self.message_handler.handle_message(message)
                            elif 'callback_query' in update:
                                callback_query = update['callback_query']
                                data = callback_query['data']
                                telegram_id = callback_query['from']['id']
                                
                                # Проверяем админ callback'и
                                if self.admin_handler and (data.startswith('admin_') or data.startswith('change_status_') or data.startswith('order_details_')):
                                    self.admin_handler.handle_callback_query(callback_query)
                                elif self.admin_handler and (data.startswith('analytics_') or data.startswith('period_')):
                                    self.admin_handler.handle_analytics_callback(callback_query)
                                elif self.admin_handler and data.startswith('export_'):
                                    self.admin_handler.handle_export_callback(callback_query)
                                elif self.admin_handler and (data.startswith('security_') or data.startswith('unblock_user_')):
                                    if hasattr(self.admin_handler, 'handle_security_callback'):
                                        self.admin_handler.handle_security_callback(callback_query)
                                    else:
                                        self.admin_handler.handle_callback_query(callback_query)
                                elif self.admin_handler and data.startswith('broadcast_'):
                                    if hasattr(self.admin_handler, 'handle_broadcast_callback'):
                                        self.admin_handler.handle_broadcast_callback(callback_query)
                                    else:
                                        self.admin_handler.handle_callback_query(callback_query)
                                else:
                                    self.message_handler.handle_callback_query(callback_query)
                        except Exception as e:
                            logger.error(f"Ошибка обработки обновления: {e}", exc_info=True)
                            self.health_monitor.increment_errors(str(e))
                else:
                    logger.warning("getUpdates returned empty/invalid — backing off")
                    time.sleep(3)
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("🛑 Бот остановлен пользователем")
        except Exception as e:
            logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        finally:
            logger.info("🔄 Закрытие соединений...")
            self.running = False
    
    def show_user_notifications(self, message):
        """Показ уведомлений пользователя"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return
        
        user_id = user_data[0][0]
        notifications = self.db.get_unread_notifications(user_id)
        
        if not notifications:
            self.send_message(
                chat_id,
                "🔔 У вас нет новых уведомлений"
            )
            return
        
        # Показываем все уведомления
        for notif in notifications:
            type_emoji = {
                'order': '📦',
                'order_status': '📋',
                'promotion': '🎁',
                'system': '⚙️',
                'info': 'ℹ️'
            }.get(notif[4], 'ℹ️')
            
            notif_text = f"{type_emoji} <b>{notif[2]}</b>\n\n"
            notif_text += f"{notif[3]}\n\n"
            notif_text += f"📅 {format_date(notif[6])}"
            
            self.send_message(chat_id, notif_text)
            
            # Отмечаем как прочитанное
            self.db.mark_notification_read(notif[0])
    
    def handle_webhook(self, provider, payload, signature=None):
        """Обработка входящих webhook'ов"""
        if not self.webhook_manager:
            return {'error': 'Webhook manager not available'}
        return self.webhook_manager.handle_payment_webhook(provider, payload, signature)
    
    def get_api_data(self, endpoint, api_key, params=None):
        """Обработка API запросов"""
        if not self.webhook_manager:
            return {'error': 'API manager not available'}
            
        try:
            from webhooks import APIManager
            api_manager = APIManager(self.db, self.security_manager)
        except ImportError:
            return {'error': 'API manager not available'}
        
        if endpoint == 'products':
            return api_manager.get_products_api(
                api_key,
                params.get('category_id') if params else None,
                params.get('limit', 50) if params else 50
            )
        elif endpoint == 'create_order':
            return api_manager.create_order_api(
                api_key,
                params['user_data'],
                params['items'],
                params['delivery_address']
            )
        else:
            return {'error': 'Unknown endpoint'}
    
    def edit_message_reply_markup(self, chat_id, message_id, reply_markup):
        """Редактирование клавиатуры сообщения"""
        url = f"{self.base_url}/editMessageReplyMarkup"
        data = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reply_markup': json.dumps(reply_markup)
        }
        
        try:
            data_encoded = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_encoded, method='POST')
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('ok', False)
        except Exception as e:
            logging.info(f"Ошибка редактирования клавиатуры: {e}")
            return False

def main():
    """Главная функция"""
    # Получение токена
    # Способ 1: Через переменную окружения (рекомендуется)
    token = BOT_TOKEN
    if not token or token == 'YOUR_BOT_TOKEN':
        logging.info("❌ ОШИБКА: Не указан токен бота!")
        logging.info("\n📋 Инструкция по настройке:")
        logging.info("1. Создайте бота через @BotFather в Telegram")
        logging.info("2. Получите токен бота")
        logging.info("3. Выберите один из способов:")
        logging.info("   СПОСОБ 1 (рекомендуется):")
        logging.info("   export TELEGRAM_BOT_TOKEN='1234567890:ABCdefGHIjklMNOpqrsTUVwxyz'")
        logging.info("   ")
        logging.info("   СПОСОБ 2 (для тестирования):")
        logging.info("   Раскомментируйте строку в main.py и вставьте токен")
        logging.info("\n🔗 Подробная инструкция в README.md")
        return
    
    # Запуск бота
    try:
        bot = TelegramShopBot(token)
        bot.run()
    except Exception as e:
        logging.info(f"❌ Ошибка запуска бота: {e}")

if __name__ == "__main__":
    main()