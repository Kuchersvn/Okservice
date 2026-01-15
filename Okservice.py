import telebot
from telebot import types
from datetime import datetime
import os
import json  # Добавлен импорт json
from openpyxl import Workbook
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, render_template, send_from_directory
import threading
import logging
from telebot import apihelper  # Добавляем для отключения прокси

# ===================== ОТКЛЮЧАЕМ ПРОКСИ =====================
apihelper.proxy = None  # Отключаем системный прокси

# ===================== НАСТРОЙКА =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PORT = int(os.getenv("PORT", 5000))
DATABASE_URL = os.getenv("DATABASE_URL")

# Параметры подключения к PostgreSQL
DB_NAME = "okservice_db"
DB_USER = "postgres"
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = "localhost"
DB_PORT = "5432"

# Инициализация
app = Flask(__name__, template_folder='templates', static_folder='static')
bot = telebot.TeleBot(BOT_TOKEN)


# ===================== ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ =====================
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
        return None


def init_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS requests (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        problem TEXT,
                        source TEXT DEFAULT 'unknown',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
        logger.info("✅ Таблица requests проверена/создана")
    except Exception as e:
        logger.error(f"⚠️ Ошибка при инициализации БД: {e}")


# ===================== FLASK РОУТЫ (САЙТ) =====================
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


@app.route("/send_request", methods=["POST"])
def send_request():
    try:
        data = request.get_json()
        name = data.get("name", "").strip()
        phone = data.get("phone", "").strip()
        problem = data.get("message", "").strip()

        if not name or not phone:
            return jsonify({"status": "error", "message": "Имя и телефон обязательны"}), 400

        # Сохраняем заявку в БД
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO requests (name, phone, problem, source)
                        VALUES (%s, %s, %s, %s);
                    """, (name, phone, problem, "site"))
                    conn.commit()
            except Exception as e:
                logger.error(f"❌ Ошибка сохранения в БД: {e}")
            finally:
                conn.close()

        # Отправляем уведомление админу в Telegram
        try:
            msg = (
                f"📬 *Новая заявка с сайта!*\n"
                f"👤 Имя: {name}\n"
                f"📞 Телефон: {phone}\n"
                f"💬 Проблема: {problem}"
            )
            bot.send_message(ADMIN_ID, msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в Telegram: {e}")

        logger.info(f"✅ Заявка с сайта: {name}, {phone}")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"❌ Ошибка обработки заявки: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ===================== TELEGRAM BOT =====================

# === Главное меню ===
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💡 О сервисе"),
        types.KeyboardButton("💰 Услуги и цены"),
        types.KeyboardButton("📸 Фото сервиса"),
        types.KeyboardButton("📍 Как добраться"),
        types.KeyboardButton("🕓 Время работы"),
        types.KeyboardButton("☎️ Связаться с нами"),
        types.KeyboardButton("🗺 Показать на карте"),
        types.KeyboardButton("💬 Оставить заявку на ремонт")
    )
    return markup


# Приветствие
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(
        message.chat.id,
        "👋 Привет! Я бот сервисного центра по ремонту компьютеров 💻\n\n"
        "Я помогу вам узнать:\n"
        "• О нашем сервисе\n"
        "• Наши услуги и цены\n"
        "• Как нас найти\n"
        "• Время работы и контакты\n"
        "• А также оставить заявку на ремонт ⚙️",
        reply_markup=main_menu()
    )


# ===================== WEB APP DATA ОБРАБОТЧИК =====================
@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    try:
        # Декодируем данные из Web App
        data = json.loads(message.web_app_data.data)

        name = data.get('name', 'Не указано')
        phone = data.get('phone', 'Не указано')
        problem = data.get('problem', 'Не указано')
        source = data.get('source', 'webapp')

        logger.info(f"📥 Получена заявка из Web App: {name}, {phone}")

        # Сохраняем в БД
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute('''
                        INSERT INTO requests (name, phone, problem, source)
                        VALUES (%s, %s, %s, %s)
                    ''', (name, phone, problem, source))
                    conn.commit()
                    logger.info(f"✅ Заявка сохранена в БД: {name}")
            except Exception as db_error:
                logger.error(f"❌ Ошибка сохранения в БД: {db_error}")
            finally:
                conn.close()
        else:
            logger.error("❌ Нет подключения к БД")

        # Отправляем подтверждение пользователю
        bot.send_message(
            message.chat.id,
            f"✅ *Заявка создана!*\n\n"
            f"👤 Имя: {name}\n"
            f"📞 Телефон: {phone}\n"
            f"📝 Проблема: {problem}\n\n"
            f"Наш мастер свяжется с вами в ближайшее время!",
            parse_mode="Markdown"
        )

        # Уведомляем админа
        bot.send_message(
            ADMIN_ID,
            f"📥 *Новая заявка из Web App!*\n"
            f"👤 Имя: {name}\n"
            f"📞 Телефон: {phone}\n"
            f"📝 Проблема: {problem}\n"
            f"🌐 Источник: {source}",
            parse_mode="Markdown"
        )

    except json.JSONDecodeError as e:
        logger.error(f"❌ Ошибка декодирования JSON: {e}")
        bot.send_message(message.chat.id, "❌ Ошибка в данных заявки")
    except Exception as e:
        logger.error(f"❌ Ошибка обработки заявки: {e}")
        bot.send_message(message.chat.id, "❌ Ошибка при создании заявки")


# ===================== АДМИН-ПАНЕЛЬ =====================

# Проверка на администратора
def is_admin(message):
    return message.chat.id == ADMIN_ID


# Админ-панель
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message):
        bot.send_message(message.chat.id, "⛔ У вас нет доступа к этой команде.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📋 Все заявки"),
        types.KeyboardButton("🔍 Найти по имени"),
        types.KeyboardButton("📤 Экспорт в Excel"),
        types.KeyboardButton("🗑 Очистить базу"),
        types.KeyboardButton("🏠 Главное меню")
    )

    bot.send_message(
        message.chat.id,
        "🛠 Добро пожаловать в панель администратора.\n\nВыберите действие:",
        reply_markup=markup
    )


# Админ: просмотр всех заявок
@bot.message_handler(func=lambda m: is_admin(m) and "все заявки" in m.text.lower())
def show_all_requests(message):
    try:
        conn = get_db_connection()
        if not conn:
            bot.send_message(message.chat.id, "❌ Ошибка подключения к БД")
            return

        with conn.cursor() as cur:
            cur.execute("SELECT id, name, phone, problem, created_at, source FROM requests ORDER BY id DESC")
            rows = cur.fetchall()

        if not rows:
            bot.send_message(message.chat.id, "📭 Заявок пока нет.")
            return

        for row in rows:
            bot.send_message(
                message.chat.id,
                f"🆔 Заявка №{row['id']}\n"
                f"👤 Имя: {row['name']}\n"
                f"📞 Телефон: {row['phone']}\n"
                f"💬 Проблема: {row['problem']}\n"
                f"🕒 Дата: {row['created_at']}\n"
                f"🌐 Источник: {row['source']}"
            )
        conn.close()
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при получении заявок: {e}")


# Админ: поиск по имени
@bot.message_handler(func=lambda m: is_admin(m) and "найти" in m.text.lower())
def find_request_by_name(message):
    bot.send_message(message.chat.id, "🔍 Введите имя для поиска:")
    bot.register_next_step_handler(message, admin_search_name)


def admin_search_name(message):
    search_name = message.text.strip()
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "❌ Ошибка подключения к БД")
        return

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM requests WHERE name ILIKE %s", (f"%{search_name}%",))
        rows = cur.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "❌ Ничего не найдено.")
        return

    for row in rows:
        bot.send_message(
            message.chat.id,
            f"🆔 Заявка №{row['id']}\n"
            f"👤 Имя: {row['name']}\n"
            f"📞 Телефон: {row['phone']}\n"
            f"💬 Проблема: {row['problem']}\n"
            f"🕒 Дата: {row['created_at']}\n"
            f"🌐 Источник: {row['source']}"
        )


# Админ: экспорт в Excel
@bot.message_handler(func=lambda m: is_admin(m) and "экспорт" in m.text.lower())
def export_to_excel(message):
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "❌ Ошибка подключения к БД")
        return

    with conn.cursor() as cur:
        cur.execute("SELECT id, name, phone, problem, created_at, source FROM requests ORDER BY id DESC")
        rows = cur.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "📭 Нет данных для экспорта.")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "Заявки"
    ws.append(["ID", "Имя", "Телефон", "Проблема", "Дата", "Источник"])

    for row in rows:
        ws.append([row["id"], row["name"], row["phone"], row["problem"], str(row["created_at"]), row["source"]])

    file_path = os.path.join(os.path.dirname(__file__), "requests.xlsx")
    wb.save(file_path)

    with open(file_path, "rb") as file:
        bot.send_document(message.chat.id, file, caption="📤 Все заявки экспортированы в Excel!")


# Админ: очистка базы
@bot.message_handler(func=lambda m: is_admin(m) and "очист" in m.text.lower())
def clear_database(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Да, удалить всё", callback_data="confirm_clear"),
        types.InlineKeyboardButton("❌ Нет", callback_data="cancel_clear")
    )
    bot.send_message(message.chat.id, "⚠️ Вы уверены, что хотите очистить базу заявок?", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ["confirm_clear", "cancel_clear"])
def clear_callback(call):
    if call.data == "confirm_clear":
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM requests")
                conn.commit()
            conn.close()
            bot.send_message(call.message.chat.id, "🧹 Все заявки успешно удалены!")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка подключения к БД")
    else:
        bot.send_message(call.message.chat.id, "❌ Отмена очистки базы.")


# Админ: возврат в главное меню
@bot.message_handler(func=lambda m: is_admin(m) and "главное меню" in m.text.lower())
def admin_to_main_menu(message):
    bot.send_message(
        message.chat.id,
        "🏠 Возвращаемся в главное меню.",
        reply_markup=main_menu()
    )


# ===================== РУЧНОЕ СОЗДАНИЕ ЗАЯВКИ =====================
def get_name(message):
    user_name = message.text
    bot.send_message(message.chat.id, "📞 Укажите ваш номер телефона:")
    bot.register_next_step_handler(message, get_phone, user_name)


def get_phone(message, user_name):
    phone = message.text
    bot.send_message(message.chat.id, "🔧 Опишите кратко проблему с компьютером:")
    bot.register_next_step_handler(message, get_problem, user_name, phone)


def get_problem(message, user_name, phone):
    problem = message.text
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO requests (name, phone, problem, source)
                    VALUES (%s, %s, %s, %s)
                """, (user_name, phone, problem, "telegram"))
                conn.commit()
            conn.close()

        bot.send_message(
            message.chat.id,
            "✅ Ваша заявка сохранена! Наш мастер скоро свяжется с вами 💙",
            reply_markup=main_menu()
        )

        bot.send_message(
            ADMIN_ID,
            f"📬 *Новая заявка из Telegram!*\n"
            f"👤 Имя: {user_name}\n"
            f"📞 Телефон: {phone}\n"
            f"💬 Проблема: {problem}\n"
            f"🕒 Время: {date}",
            parse_mode="Markdown"
        )

        logger.info(f"✅ Заявка из Telegram сохранена: {user_name}, {phone}, {problem}")

    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении заявки из Telegram: {e}")
        bot.send_message(
            message.chat.id,
            "⚠️ Произошла ошибка при сохранении заявки. Попробуйте позже 🙏",
            reply_markup=main_menu()
        )


# ===================== ОСНОВНОЕ МЕНЮ =====================
@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text.lower()

    if "о сервисе" in text:
        bot.send_message(
            message.chat.id,
            "🧰 *О нашем сервисе*\n\n"
            "Мы — профессиональный сервис по ремонту компьютеров и ноутбуков.\n"
            "✅ Более 5 лет опыта\n"
            "✅ Гарантия до 1 года\n"
            "✅ Срочный ремонт за 1 час\n"
            "✅ Бесплатная диагностика\n\n"
            "💙 Надёжный сервис, которому доверяют тысячи клиентов!",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    elif "услуги" in text or "цены" in text:
        bot.send_message(
            message.chat.id,
            "💰 *Наши услуги и цены:*\n\n"
            "1️⃣ Диагностика компьютера — *бесплатно*\n"
            "2️⃣ Установка Windows / Linux / macOS — *от 10000 тенге*\n"
            "3️⃣ Чистка от пыли + замена термопасты — *от 10000 тенге*\n"
            "4️⃣ Прошивка BIOS — * от 6000 тенге*\n"
            "5️⃣ Замена кулера, термопрокладок — *от 5000 тенге*\n"
            "6️⃣ Восстановление данных с HDD / SSD — *от 12000 тенге*\n"
            "7️⃣ Замена экрана ноутбука — *от 10000 тенге*\n"
            "8️⃣ Ремонт материнской платы — *от 15000 тенге*\n"
            "9️⃣ Замена клавиатуры ноутбука — *от 5000 тенге*\n"
            "🔟 Ремонт телевизоров — *от 5000 тенге*\n\n"
            "1️⃣1️⃣ Ремонт электросамокатов - *от 5000 тенге*\n\n"
            "1️⃣2️⃣ Ремонт смартфонов - *от 5000 тенге*\n\n "
            "💡 Все работы выполняются с гарантией до 12 месяцев!",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    elif "фото" in text:
        try:
            photo_path = os.path.join(os.path.dirname(__file__), "photos", "service_photo.jpg")
            if os.path.exists(photo_path):
                with open(photo_path, "rb") as photo:
                    bot.send_photo(
                        message.chat.id,
                        photo,
                        caption="📸 Наш уютный сервисный центр!\nСовременное оборудование и опытные мастера 👨‍🔧",
                        reply_markup=main_menu()
                    )
            else:
                bot.send_message(message.chat.id, "⚠️ Фото не найдено в папке photos.", reply_markup=main_menu())
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка при отправке фото: {e}", reply_markup=main_menu())

    elif "как добраться" in text or "адрес" in text:
        bot.send_message(
            message.chat.id,
            "📍 *Адрес:* г. Уральск, проспект Нурсултана Назарбаева, 240/1\n"
            "🚌 Остановка *Маншук Маметовой* — 5 минут пешком.\n\n"
            "🗺 [Открыть в Яндекс.Картах](https://yandex.ru/maps/?text=Уральск, проспект Нурсултана Назарбаева, 240/1)",
            parse_mode="Markdown",
            disable_web_page_preview=False,
            reply_markup=main_menu()
        )

    elif "время работы" in text:
        bot.send_message(
            message.chat.id,
            "🕓 *Время работы:*\nПн–Сб: 10:00–19:00\nВс: 10:00–19:00",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    elif "связаться" in text or "контакт" in text:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📞 Позвонить", url="https://t.me/share/url?url=tel:+7064295545"),
            types.InlineKeyboardButton("💬 WhatsApp", url="https://wa.me/7064295545"),
            types.InlineKeyboardButton("✈️ Telegram", url="https://t.me/@Fixuralsk"),
            types.InlineKeyboardButton("📸 Instagram", url="https://instagram.com/okservice_uralsk"),
        )

        bot.send_message(
            message.chat.id,
            "📱 *Контакты сервисного центра:*\n\n"
            "👨‍🔧 *Ок Service — ремонт компьютеров и ноутбуков*\n\n"
            "📞 Телефон: +7 (706) 429-55-45\n"
            "💬 WhatsApp: +7 (706) 429-55-45\n"
            "✈️ Telegram: [@Fixuralsk](https://t.me/yourusername)\n"
            "📸 Instagram: [@okservice_uralsk](https://instagram.com/okservice_uralsk)\n"
            "Выберите удобный способ связи 👇",
            parse_mode="Markdown",
            disable_web_page_preview=False,
            reply_markup=markup
        )

    elif "карта" in text or "показать" in text:
        latitude = 51.221450
        longitude = 51.363653
        bot.send_location(message.chat.id, latitude, longitude)
        bot.send_message(message.chat.id, "📍 Наш сервис здесь!", reply_markup=main_menu())

    elif "заявк" in text or "ремонт" in text:
        bot.send_message(
            message.chat.id,
            "📝 *Оставить заявку на ремонт*\n\n"
            "Вы можете:\n"
            "1. Нажать кнопку ниже для быстрой формы 📱\n"
            "2. Или написать данные вручную ✍️\n\n"
            "Выберите вариант:",
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardRemove()
        )



        # Также предлагаем ручной ввод
        bot.send_message(
            message.chat.id,
            "Или напишите свои данные:\n\n"
            "Введите ваше имя:"
        )
        bot.register_next_step_handler(message, get_name)


# ===================== ЗАПУСК =====================
def run_flask():
    """Запуск Flask сервера"""
    init_db()
    logger.info(f"🌐 Веб-сайт запущен: http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)


def run_bot():
    """Запуск Telegram бота"""
    logger.info("🤖 Telegram бот запускается...")
    bot.remove_webhook()
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except Exception as e:
        logger.error(f"❌ Ошибка бота: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Запуск сервисного центра OK Service")
    print("=" * 50)

    # Создаем необходимые папки
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('photos', exist_ok=True)

    # Инициализация БД
    try:
        init_db()
        print("✅ База данных готова")
    except Exception as e:
        print(f"⚠️ Ошибка БД: {e}")

    # Запускаем в разных потоках
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    bot_thread = threading.Thread(target=run_bot, daemon=True)

    flask_thread.start()
    bot_thread.start()

    print(f"\n✅ Система запущена!")
    print(f"🌐 Сайт: http://localhost:{PORT}")
    print(f"🤖 Бот: активен")
    print("\n📋 Для остановки нажмите Ctrl+C")
    print("=" * 50)

    try:
        # Держим основной поток активным
        flask_thread.join()
        bot_thread.join()
    except KeyboardInterrupt:
        print("\n\n🛑 Система остановлена")
