import logging
import os
from datetime import timedelta
from io import BytesIO

from aiohttp import ClientSession
from PIL import Image


logger = logging.getLogger(__name__)


class PrinterAPI:
    def __init__(self):
        self.session = ClientSession(
            headers={
                'CF-Access-Client-Id': os.getenv('CLOUDFLARE_AC_ID', 'id'),
                'CF-Access-Client-Secret': os.getenv(
                    'CLOUDFLARE_AC_SECRET', 'secret'),
            },
            raise_for_status=self.response_error,
        )
        self.printer_url = os.getenv('PRINTER_URL', 'printer_url')
        self.klippy_states = {
            'ready': 'Klippy инициализирован и готов к командам.',
            'startup': 'Klippy находится в процессе запуска.',
            'error': 'Klippy столкнулся с ошибкой во время запуска.',
            'shutdown': (
                'Klippy находится в состоянии завершения работы. '
                'Это может быть инициировано пользователем через аварийную '
                'остановку или программным обеспечением в случае критической '
                'ошибки во время работы.'
            ),
        }

    async def photo(self):
        try:
            logger.debug('Запрос снимка камеры')
            async with self.session.get(
                    self.printer_url + '/webcam/?action=snapshot') as response:
                image_bytes = await response.read()
            with Image.open(BytesIO(image_bytes)) as image:
                rotated_image = image.rotate(180)
                output = BytesIO()
                rotated_image.save(output, format=image.format or 'JPEG')
                return output.getvalue()
        except Exception as e:
            logger.exception('Ошибка получения фото')
            return str(e)

    async def printer_info(self):
        try:
            async with self.session.get(
                    self.printer_url + '/printer/info') as response:
                data = await response.json()
                state = data['result']['state']
                logger.info(f'Состояние Klippy: {state}')
                return self.klippy_states[state]
        except Exception as e:
            logger.exception('Ошибка получения информации о принтере')
            return str(e)

    async def proc_stats(self):
        try:
            async with self.session.get(
                    self.printer_url + '/machine/proc_stats') as response:
                data = await response.json()
                result = data['result']
                cpu_usage = result['system_cpu_usage']['cpu']
                cpu_temp = result['cpu_temp']
                throttled_state = result['throttled_state']
                ram_usage = (result['system_memory']['used'] * 100
                             / result['system_memory']['total'])
                logger.debug(
                    f'proc stats cpu={cpu_usage:.2f} '
                    f'temp={cpu_temp:.2f} throttled={throttled_state} '
                    f'ram={ram_usage:.2f}')
                return (
                    f'Загрузка процессора: {round(cpu_usage)}%\n' +
                    f'Температура процессора: {round(cpu_temp)}°C\n' +
                    f'Троттлинг: {"да" if throttled_state else "нет"}\n' +
                    f'Загрузка ОЗУ: {round(ram_usage)}%\n'
                )
        except Exception as e:
            logger.exception('Ошибка получения статусов системы')
            return str(e)

    async def _get_print_status(self):
        async with self.session.get(
                self.printer_url + '/printer/objects/query?'
                + 'webhooks&virtual_sdcard&print_stats') as response:
            data = await response.json()
        return data['result']['status']

    async def print_status(self):
        try:
            status = await self._get_print_status()
            logger.debug(f'Сырые данные статуса печати: {status}')
            if status['webhooks']['state'] != 'ready':
                return 'Принтер не готов: ' + status['webhooks']['message']
            if status['print_stats']['state'] == 'standby':
                return 'Принтер в ожидании'
            if status['print_stats']['state'] == 'error':
                return 'Ошибка: ' + status['print_stats']['message']
            filename = status['print_stats']['filename']
            if status['print_stats']['state'] == 'complete':
                return 'Печать завершена: ' + filename
            async with self.session.get(
                    self.printer_url + '/server/files/metadata?'
                    + 'filename=' + filename) as file_response:
                file_data = await file_response.json()
                estimated_time = file_data['result']['estimated_time']
            prog_time = (status['virtual_sdcard']['progress'] * estimated_time)
            eta = str(timedelta(
                seconds=(estimated_time - prog_time))).split('.')[0]
            print_states = {
                'printing': 'Печатается',
                'paused': 'Пауза',
            }
            return (
                f'{print_states[status["print_stats"]["state"]]}: '
                f'{filename}\n'
                f'Прогресс: {round(
                    status["virtual_sdcard"]["progress"] * 100)}%\n'
                f'Оставшееся время: {eta}'
            )
        except Exception as e:
            logger.exception('Ошибка получения статуса печати')
            return str(e)

    async def current_print_state(self):
        status = await self._get_print_status()
        logger.debug(f'Текущее состояние печати: {status}')
        if status['webhooks']['state'] != 'ready':
            message = status['webhooks'].get('message', 'Принтер не готов')
            return 'not_ready', 'Принтер не готов: ' + message

        print_state = status['print_stats']['state']
        filename = status['print_stats'].get('filename')
        filename_suffix = f': {filename}' if filename else ''

        if print_state == 'printing':
            return 'printing', None
        if print_state == 'paused':
            return 'paused', f'Печать на паузе{filename_suffix}'
        if print_state == 'complete':
            return 'complete', f'Печать завершена{filename_suffix}'
        if print_state == 'error':
            error_message = status['print_stats'].get('message')
            if error_message:
                return 'error', f'Ошибка печати: {error_message}'
            return 'error', 'Ошибка печати'
        if print_state == 'standby':
            return 'standby', 'Принтер в ожидании'
        return print_state, f'Неизвестное состояние печати: {print_state}'

    async def response_error(self, response):
        if response.status == 530:
            raise RuntimeError(
                'Статус 530: Принтер выключен или находится не в сети.')
        if not response.ok:
            logger.warning(
                f'HTTP статус {response.status}: {response.reason}')
            raise RuntimeError(
                f'Статус {response.status}: {response.reason}')

    async def close(self):
        await self.session.close()
