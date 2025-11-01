import telebot
from telebot import types
import sqlite3
from datetime import datetime
import os
from openpyxl import Workbook

# === Настройки ===
ADMIN_ID = 7038896865
BOT_TOKEN = "8350965046:AAE0YvEzYvauGchb8tGiWoLMUvL8NFmSAyk"
bot = telebot.TeleBot(BOT_TOKEN)

# === Подключение к БД ===
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    problem TEXT,
    date TEXT
)
""")
conn.commit()

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


# === Приветствие ===
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


# === Проверка на администратора ===
def is_admin(message):
    return message.chat.id == ADMIN_ID


# === Админ-панель ===
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


# === Админ: просмотр всех заявок ===
@bot.message_handler(func=lambda m: is_admin(m) and "все заявки" in m.text.lower())
def show_all_requests(message):
    cursor.execute("SELECT * FROM requests ORDER BY id DESC")
    rows = cursor.fetchall()

    if not rows:
        bot.send_message(message.chat.id, "📭 Заявок пока нет.")
        return

    for row in rows:
        req_id, name, phone, problem, date = row
        bot.send_message(
            message.chat.id,
            f"🆔 Заявка №{req_id}\n"
            f"👤 Имя: {name}\n"
            f"📞 Телефон: {phone}\n"
            f"💬 Проблема: {problem}\n"
            f"🕒 Дата: {date}"
        )


# === Админ: поиск по имени ===
@bot.message_handler(func=lambda m: is_admin(m) and "найти" in m.text.lower())
def find_request_by_name(message):
    bot.send_message(message.chat.id, "🔍 Введите имя для поиска:")
    bot.register_next_step_handler(message, admin_search_name)


def admin_search_name(message):
    name = message.text.strip()
    cursor.execute("SELECT * FROM requests WHERE name LIKE ?", (f"%{name}%",))
    rows = cursor.fetchall()

    if not rows:
        bot.send_message(message.chat.id, "❌ Ничего не найдено.")
        return

    for row in rows:
        req_id, name, phone, problem, date = row
        bot.send_message(
            message.chat.id,
            f"🆔 Заявка №{req_id}\n"
            f"👤 Имя: {name}\n"
            f"📞 Телефон: {phone}\n"
            f"💬 Проблема: {problem}\n"
            f"🕒 Дата: {date}"
        )


# === Админ: экспорт в Excel ===
@bot.message_handler(func=lambda m: is_admin(m) and "экспорт" in m.text.lower())
def export_to_excel(message):
    cursor.execute("SELECT * FROM requests ORDER BY id DESC")
    rows = cursor.fetchall()

    if not rows:
        bot.send_message(message.chat.id, "📭 Нет данных для экспорта.")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "Заявки"
    ws.append(["ID", "Имя", "Телефон", "Проблема", "Дата"])

    for row in rows:
        ws.append(row)

    file_path = os.path.join(os.path.dirname(__file__), "requests.xlsx")
    wb.save(file_path)

    with open(file_path, "rb") as file:
        bot.send_document(message.chat.id, file, caption="📤 Все заявки экспортированы в Excel!")


# === Админ: очистка базы ===
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
        cursor.execute("DELETE FROM requests")
        conn.commit()
        bot.send_message(call.message.chat.id, "🧹 Все заявки успешно удалены!")
    else:
        bot.send_message(call.message.chat.id, "❌ Отмена очистки базы.")


# === Пользовательские функции ===
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

    cursor.execute("INSERT INTO requests (name, phone, problem, date) VALUES (?, ?, ?, ?)",
                   (user_name, phone, problem, date))
    conn.commit()

    bot.send_message(
        message.chat.id,
        "✅ Ваша заявка сохранена! Наш мастер скоро свяжется с вами 💙",
        reply_markup=main_menu()
    )

    bot.send_message(
        ADMIN_ID,
        f"📬 *Новая заявка!*\n"
        f"👤 Имя: {user_name}\n"
        f"📞 Телефон: {phone}\n"
        f"💬 Проблема: {problem}\n"
        f"🕒 Время: {date}",
        parse_mode="Markdown"
    )


# === Основное меню ===
@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text.lower()

    if "о сервисе" in text:
        bot.send_message(
            message.chat.id,
            "🧰 *О нашем сервисе*\n\n"
            "Мы — профессиональный сервис по ремонту компьютеров и ноутбуков.\n"
            "✅ Более 10 лет опыта\n"
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
            "2️⃣ Установка Windows / Linux / macOS — *от 1500 ₽*\n"
            "3️⃣ Чистка от пыли + замена термопасты — *от 1200 ₽*\n"
            "4️⃣ Настройка Wi-Fi, сети и принтера — *1000 ₽*\n"
            "5️⃣ Замена кулера, термопрокладок — *от 800 ₽*\n"
            "6️⃣ Восстановление данных с HDD / SSD — *от 2500 ₽*\n"
            "7️⃣ Замена экрана ноутбука — *от 3500 ₽*\n"
            "8️⃣ Ремонт материнской платы — *от 4000 ₽*\n"
            "9️⃣ Замена клавиатуры ноутбука — *от 2000 ₽*\n"
            "🔟 Удаление вирусов и оптимизация системы — *от 800 ₽*\n\n"
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
            types.InlineKeyboardButton("📞 Позвонить", url="https://t.me/share/url?url=tel:+79991234567"),
            types.InlineKeyboardButton("💬 WhatsApp", url="https://wa.me/7064295545"),
            types.InlineKeyboardButton("✈️ Telegram", url="https://t.me/@Fixuralsk"),
            types.InlineKeyboardButton("📸 Instagram", url="https://instagram.com/okservice_uralsk"),
            types.InlineKeyboardButton("🌐 Сайт", url="https://pcservice.ru")
        )

        bot.send_message(
            message.chat.id,
            "📱 *Контакты сервисного центра:*\n\n"
            "👨‍🔧 *Ок Service — ремонт компьютеров и ноутбуков*\n\n"
            "📞 Телефон: +7 (706) 429-55-45\n"
            "💬 WhatsApp: +7 (706) 429-55-45\n"
            "✈️ Telegram: [@Fixuralsk](https://t.me/yourusername)\n"
            "📸 Instagram: [@okservice_uralsk](https://instagram.com/okservice_uralsk)\n"
            "🌍 Сайт: [pcservice.ru](https://pcservice.ru)\n\n"
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
        bot.send_message(message.chat.id, "📝 Отлично! Давайте оформим заявку. Как вас зовут?")
        bot.register_next_step_handler(message, get_name)

    else:
        bot.send_message(message.chat.id, "🤔 Я вас не понял. Выберите нужный раздел из меню 👇", reply_markup=main_menu())


# === Запуск ===
print("🤖 Бот запущен и готов к работе...")
bot.polling(none_stop=True)
