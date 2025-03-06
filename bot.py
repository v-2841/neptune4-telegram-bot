import os

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (Application, ApplicationBuilder, CommandHandler,
                          ContextTypes, MessageHandler)
from telegram.ext.filters import Chat, Regex, Text

from printer import PrinterAPI


load_dotenv()


def filter_chat_ids(app: Application) -> None:
    """
    Добавляет фильтр для чатов из переменной окружения
    TELEGRAM_CHAT_IDS, если она задана.
    """
    chat_ids = os.getenv('TELEGRAM_CHAT_IDS', '')
    if chat_ids:
        app.add_handler(MessageHandler(~Chat(
            set(int(id.strip()) for id in chat_ids.split(','))), forbidden))


def create_main_menu() -> ReplyKeyboardMarkup:
    """Создает клавиатуру."""
    return ReplyKeyboardMarkup(
        [["Состояние принтера", "Состояние оборудования"],
         ["Состояние печати"]],
        resize_keyboard=True, is_persistent=True,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отправляет приветственное сообщение.
    """
    await update.message.reply_text(
        'Привет!', reply_markup=create_main_menu())


async def printer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет состояние принтера."""
    printer_api: PrinterAPI = context.bot_data['printer_api']
    result = await printer_api.printer_info()
    await update.message.reply_text(result)


async def proc_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет состояние оборудования."""
    printer_api: PrinterAPI = context.bot_data['printer_api']
    result = await printer_api.proc_stats()
    await update.message.reply_text(result)


async def print_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет состояние печати."""
    printer_api: PrinterAPI = context.bot_data['printer_api']
    result = await printer_api.print_status()
    await update.message.reply_text(result)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение об ошибке."""
    await update.message.reply_text(
        'Неизвестная команда', reply_markup=create_main_menu())


async def forbidden(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение о запрете в доступе."""
    await update.message.reply_text('Доступ запрещен')


async def post_init(application: Application):
    """Инициализация бота."""
    application.bot_data['printer_api'] = PrinterAPI()


async def post_shutdown(application: Application):
    """Завершение работы бота."""
    await application.bot_data['printer_api'].close()


if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv(
        'TELEGRAM_BOT_TOKEN', 'token')).post_init(post_init).post_shutdown(
            post_shutdown).build()
    filter_chat_ids(app)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        Regex("^Состояние принтера$"), printer_info))
    app.add_handler(MessageHandler(
        Regex("^Состояние оборудования$"), proc_stats))
    app.add_handler(MessageHandler(
        Regex("^Состояние печати$"), print_status))
    app.add_handler(MessageHandler(Text(), unknown_command))
    app.run_polling()
