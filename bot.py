import json
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (Application, ApplicationBuilder, CommandHandler,
                          ContextTypes)

from printer import PrinterAPI


load_dotenv()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    printer_api: PrinterAPI = context.bot_data['printer_api']
    config = await printer_api.printer_info()
    await update.message.reply_text(json.dumps(
        config, sort_keys=True, indent=4))


async def post_init(application: Application) -> None:
    application.bot_data['printer_api'] = PrinterAPI()


async def post_shutdown(application: Application) -> None:
    await application.bot_data['printer_api'].close()


if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv(
        'TELEGRAM_BOT_TOKEN', 'token')).post_init(post_init).post_shutdown(
            post_shutdown).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
