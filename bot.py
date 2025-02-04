import os

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (Application, ApplicationBuilder, CommandHandler,
                          ContextTypes, MessageHandler)
from telegram.ext.filters import Regex, Text

from printer import PrinterAPI


load_dotenv()


def create_main_menu() -> ReplyKeyboardMarkup:
    """Создает главное меню."""
    return ReplyKeyboardMarkup(
        [["Состояние принтера"]],
        resize_keyboard=True, is_persistent=True,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Привет!', reply_markup=create_main_menu())


async def printer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    printer_api: PrinterAPI = context.bot_data['printer_api']
    result = await printer_api.printer_info()
    await update.message.reply_text(result)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Неизвестная команда', reply_markup=create_main_menu())


async def post_init(application: Application):
    application.bot_data['printer_api'] = PrinterAPI()


async def post_shutdown(application: Application):
    await application.bot_data['printer_api'].close()


if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv(
        'TELEGRAM_BOT_TOKEN', 'token')).post_init(post_init).post_shutdown(
            post_shutdown).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        Regex("^Состояние принтера$"), printer_info))
    app.add_handler(MessageHandler(Text(), unknown_command))
    app.run_polling()
