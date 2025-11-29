import logging
import os

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (Application, ApplicationBuilder, CommandHandler,
                          ContextTypes, MessageHandler)
from telegram.ext.filters import Chat, Regex, Text

from printer import PrinterAPI


PRINT_MONITOR_JOB_KEY = 'print_monitor_job'
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
load_dotenv()


def filter_chat_ids(app: Application) -> None:
    chat_ids = os.getenv('TELEGRAM_CHAT_IDS', '')
    if chat_ids:
        app.add_handler(MessageHandler(~Chat(
            set(int(id.strip()) for id in chat_ids.split(','))), forbidden))


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ['Состояние принтера', 'Состояние оборудования'],
            ['Состояние печати', 'Фото'],
            ['Режим печати'],
        ],
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'Команда /start от chat={update.effective_chat.id}')
    await update.message.reply_text(
        'Привет!', reply_markup=main_menu())


async def printer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(
        f'Запрошено состояние принтера chat={update.effective_chat.id}')
    printer_api: PrinterAPI = context.bot_data['printer_api']
    result = await printer_api.printer_info()
    await update.message.reply_text(result)


async def proc_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(
        f'Запрошено состояние оборудования chat={update.effective_chat.id}')
    printer_api: PrinterAPI = context.bot_data['printer_api']
    result = await printer_api.proc_stats()
    await update.message.reply_text(result)


async def print_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(
        f'Запрошено состояние печати chat={update.effective_chat.id}')
    printer_api: PrinterAPI = context.bot_data['printer_api']
    result = await printer_api.print_status()
    await update.message.reply_text(result)


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'Запрошено фото chat={update.effective_chat.id}')
    printer_api: PrinterAPI = context.bot_data['printer_api']
    try:
        photo = await printer_api.photo()
        await update.message.reply_photo(photo)
    except Exception:
        logger.exception(
            f'Ошибка при получении фото chat={update.effective_chat.id}')
        await update.message.reply_text('Ошибка при получении фото')


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(
        f'Неизвестная команда chat={update.effective_chat.id} '
        f'text={update.message.text}')
    await update.message.reply_text(
        'Неизвестная команда', reply_markup=main_menu())


async def forbidden(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f'Доступ запрещен для chat={update.effective_chat.id}')
    await update.message.reply_text('Доступ запрещен')


async def post_init(application: Application):
    logger.info('Инициализация бота')
    application.bot_data['printer_api'] = PrinterAPI()


async def post_shutdown(application: Application):
    logger.info('Завершение работы бота')
    await application.bot_data['printer_api'].close()


async def print_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    existing_job = context.chat_data.get(PRINT_MONITOR_JOB_KEY)
    if existing_job:
        logger.info(f'Print monitor already active '
                    f'for chat {update.effective_chat.id}')
        await update.message.reply_text(
            'Уже слежу за печатью. Остановлюсь, как только она завершится '
            'или прервётся.',
            reply_markup=main_menu(),
        )
        return

    logger.info(f'Enable print monitor for chat {update.effective_chat.id}')
    job = context.job_queue.run_repeating(
        check_print_job,
        interval=60,
        first=5,
        chat_id=update.effective_chat.id,
        name=f'print-monitor-{update.effective_chat.id}',
    )
    context.chat_data[PRINT_MONITOR_JOB_KEY] = job
    await update.message.reply_text(
        'Включил режим печати. Проверяю состояние каждую минуту.',
        reply_markup=main_menu(),
    )


async def check_print_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    printer_api: PrinterAPI = context.bot_data['printer_api']
    try:
        state, message = await printer_api.current_print_state()
    except Exception:
        logger.exception(
            f'Printer state check failed for chat {job.chat_id}')
        await context.bot.send_message(
            chat_id=job.chat_id,
            text='Нет соединения с принтером. Останавливаю проверки.',
        )
        stop_print_monitoring(context.chat_data, job)
        return

    if state == 'printing':
        logger.debug(f'Print continues normally; chat={job.chat_id}')
        return

    logger.info(
        f'Print state changed: chat={job.chat_id} state={state} '
        f'message={message}')
    await context.bot.send_message(
        chat_id=job.chat_id,
        text=message or 'Печать остановлена. Останавливаю проверки.',
    )
    stop_print_monitoring(context.chat_data, job)


def stop_print_monitoring(chat_data, job):
    if job:
        job.schedule_removal()
    chat_data.pop(PRINT_MONITOR_JOB_KEY, None)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s')
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
    app.add_handler(MessageHandler(
        Regex('^Режим печати$'), print_mode))
    app.add_handler(MessageHandler(Regex('^Фото$'), photo))
    app.add_handler(MessageHandler(Text(), unknown_command))
    app.run_polling()
