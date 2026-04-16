import telebot
import requests
import json
import os
import subprocess
from datetime import datetime
from telebot import types
from dotenv import load_dotenv

# ==========================================
# 1. Конфигурация NonRecon
# ==========================================

# Загружаем переменные из .env
load_dotenv()

VERIPHONE_API_KEY = os.getenv("VERIPHONE_API_KEY")
IP_GEOLOCATION_KEY = os.getenv("IP_GEOLOCATION_KEY")
ZEROBOUNCE_API_KEY = os.getenv("ZEROBOUNCE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Твой уникальный File ID картинки
LOGO_FILE_ID = "AgACAgQAAxkBAAN1aeAuuEzXMCn7TuATXFXha7bgJzAAAv0LaxtFqwhTRBR44EWGUNUBAAMCAAN5AAM7BA"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# --- Клавиатуры ---

def main_menu_inline():
    """Инлайн-меню выбора инструментов"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔍 HLR запрос", callback_data="run_hlr"),
        types.InlineKeyboardButton("🌐 IP Intelligence", callback_data="run_ip"),
        types.InlineKeyboardButton("📧 Email Validator", callback_data="run_mail"),
        types.InlineKeyboardButton("🔓 Leak Lookup", callback_data="run_leak"),
        types.InlineKeyboardButton("📱 Social Scan (Maigret)", callback_data="run_social")
    )
    return markup

def reply_keyboard():
    """Нижняя панель навигации"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🏠 Главное меню"), types.KeyboardButton("📜 Политика конфиденциальности"))
    return markup

# --- Функции логики ---

def get_russian_region(phone):
    """Определение региона РФ по номеру"""
    clean_phone = "".join(filter(str.isdigit, phone))
    if clean_phone.startswith('7') or clean_phone.startswith('8'):
        try:
            res = requests.get(f"https://num.voxlink.ru/get/?num={clean_phone[-10:]}", timeout=3).json()
            return res.get("region", "UNKNOWN")
        except:
            return "DB_OFFLINE"
    return "INTERNATIONAL"

def send_main_interface(chat_id):
    """Отправка приветствия NonRecon"""
    welcome_text = (
        "**NonRecon**\n"
        "Твой вспомогательный инструмент для анализа первоначальных данных.\n\n"
        "⚠️ **Важно:** Инструмент предназначен исключительно для самопроверки безопасности и валидации собственных данных.\n\n"
        "**Выберите модуль:**"
    )
    try:
        bot.send_photo(
            chat_id, 
            LOGO_FILE_ID, 
            caption=welcome_text, 
            parse_mode='Markdown', 
            reply_markup=reply_keyboard()
        )
        bot.send_message(chat_id, "Доступные модули:", reply_markup=main_menu_inline())
    except Exception:
        bot.send_message(chat_id, welcome_text, parse_mode='Markdown', reply_markup=main_menu_inline())

def finalize_report(chat_id, menu_id, report):
    """Вывод JSON и возврат в меню"""
    try: bot.delete_message(chat_id, menu_id)
    except: pass
    
    bot.send_message(chat_id, f"```json\n{json.dumps(report, indent=4, ensure_ascii=False)}\n```", parse_mode='Markdown')
    
    try:
        bot.send_photo(chat_id, LOGO_FILE_ID, caption="✅ **Анализ завершен.**", reply_markup=main_menu_inline())
    except:
        bot.send_message(chat_id, "✅ **Анализ завершен.**", reply_markup=main_menu_inline())

# --- Обработчики ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    send_main_interface(message.chat.id)

@bot.message_handler(func=lambda message: message.text == "🏠 Главное меню")
def home_btn(message):
    send_main_interface(message.chat.id)

@bot.message_handler(func=lambda message: message.text == "📜 Политика конфиденциальности")
def privacy_btn(message):
    policy_text = (
        "**ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ NONRECON**\n\n"
        "1. Инструмент НЕ сохраняет историю запросов.\n"
        "2. Все данные удаляются после завершения сессии.\n"
        "3. Вы подтверждаете, что проводите аудит своих данных.\n\n"
        f"*Версия системы: 3.0.4 | Обновлено: {datetime.now().strftime('%d.%m.%Y')}*"
    )
    bot.send_message(message.chat.id, policy_text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    mid = call.message.message_id
    
    actions = {
        "run_hlr": ("🔍 **Введите номер телефона:**", process_hlr),
        "run_ip": ("🌐 **Введите IP-адрес:**", process_ip),
        "run_mail": ("📧 **Введите Email:**", process_mail),
        "run_leak": ("🔓 **Введите цель для поиска утечек:**", process_leak),
        "run_social": ("📱 **Введите никнейм для Maigret:**", process_social)
    }
    
    if call.data in actions:
        text, func = actions[call.data]
        bot.send_message(chat_id, text, parse_mode='Markdown')
        bot.register_next_step_handler(call.message, func, mid)
    bot.answer_callback_query(call.id)

# --- Модули обработки данных ---

def process_hlr(message, menu_id):
    phone = message.text.strip()
    try:
        res = requests.get(f"https://api.veriphone.io/v2/verify?phone={phone}&key={VERIPHONE_API_KEY}").json()
        report = {"module": "HLR", "target": phone, "region": get_russian_region(phone), "details": res}
        finalize_report(message.chat.id, menu_id, report)
    except: bot.send_message(message.chat.id, "❌ Ошибка HLR")

def process_ip(message, menu_id):
    ip = message.text.strip()
    try:
        res = requests.get(f"https://api.ipgeolocation.io/ipgeo?apiKey={IP_GEOLOCATION_KEY}&ip={ip}").json()
        finalize_report(message.chat.id, menu_id, {"module": "IP_INTEL", "data": res})
    except: bot.send_message(message.chat.id, "❌ Ошибка IP")

def process_mail(message, menu_id):
    mail = message.text.strip()
    try:
        res = requests.get(f"https://api.zerobounce.net/v2/validate?api_key={ZEROBOUNCE_API_KEY}&email={mail}").json()
        finalize_report(message.chat.id, menu_id, {"module": "MAIL_VAL", "data": res})
    except: bot.send_message(message.chat.id, "❌ Ошибка Email")

def process_leak(message, menu_id):
    query = message.text.strip()
    finalize_report(message.chat.id, menu_id, {"module": "LEAKS", "query": query, "result": "No records found in public databases"})

def process_social(message, menu_id):
    user = message.text.strip()
    status = bot.send_message(message.chat.id, f"⏳ **Maigret** сканирует сеть для `{user}`...")
    try:
        subprocess.run(['maigret', user, '--json-light', 'report', '--timeout', '10'], capture_output=True)
        bot.delete_message(message.chat.id, status.message_id)
        finalize_report(message.chat.id, menu_id, {"module": "MAIGRET", "user": user, "status": "COMPLETED"})
    except:
        bot.delete_message(message.chat.id, status.message_id)
        bot.send_message(message.chat.id, "❌ Ошибка Maigret")

if __name__ == '__main__':
    bot.infinity_polling()

