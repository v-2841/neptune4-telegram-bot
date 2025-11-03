import os

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (Application, ApplicationBuilder, CommandHandler,
                          ContextTypes, MessageHandler)
from telegram.ext.filters import Chat, Regex, Text

from printer import PrinterAPI


load_dotenv()


def filter_chat_ids(app: Application) -> None:
    chat_ids = os.getenv('TELEGRAM_CHAT_IDS', '')
    if chat_ids:
        app.add_handler(MessageHandler(~Chat(
            set(int(id.strip()) for id in chat_ids.split(','))), forbidden))


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [['Состояние принтера', 'Состояние оборудования'],
         ['Состояние печати', 'Фото']],
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Привет!', reply_markup=main_menu())


async def printer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    printer_api: PrinterAPI = context.bot_data['printer_api']
    result = await printer_api.printer_info()
    await update.message.reply_text(result)


async def proc_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    printer_api: PrinterAPI = context.bot_data['printer_api']
    result = await printer_api.proc_stats()
    await update.message.reply_text(result)


async def print_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    printer_api: PrinterAPI = context.bot_data['printer_api']
    result = await printer_api.print_status()
    await update.message.reply_text(result)


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    printer_api: PrinterAPI = context.bot_data['printer_api']
    try:
        photo = await printer_api.photo()
        await update.message.reply_photo(photo)
    except Exception:
        await update.message.reply_text('Ошибка при получении фото')


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Неизвестная команда', reply_markup=main_menu())


async def forbidden(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Доступ запрещен')


async def post_init(application: Application):
    application.bot_data['printer_api'] = PrinterAPI()


async def post_shutdown(application: Application):
    await application.bot_data['printer_api'].close()


if __name__ == '__main__':
    app = ApplicationBuilder().token(os.getenv(
        'TELEGRAM_BOT_TOKEN', 'token')).post_init(post_init).post_shutdown(
            post_shutdown).build()
    filter_chat_ids(app)
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(
        Regex('^Состояние принтера$'), printer_info))
    app.add_handler(MessageHandler(
        Regex('^Состояние оборудования$'), proc_stats))
    app.add_handler(MessageHandler(
        Regex('^Состояние печати$'), print_status))
    app.add_handler(MessageHandler(Regex('^Фото$'), photo))
    app.add_handler(MessageHandler(Text(), unknown_command))
    app.run_polling()
