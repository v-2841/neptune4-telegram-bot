import os

from aiohttp import ClientSession


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

    async def printer_info(self):
        try:
            async with self.session.get(
                    self.printer_url + '/printer/info') as response:
                data = await response.json()
                return data['result']['state_message']
        except Exception as e:
            return str(e)

    # async def proc_stats(self):
    #     async with self.session.get(
    #             self.printer_url + '/machine/proc_stats') as response:
    #         return await response.json()

    # async def server_config(self):
    #     async with self.session.get(
    #             self.printer_url + '/server/config') as response:
    #         return await response.json()

    async def response_error(self, response):
        if response.status == 530:
            raise RuntimeError(
                'Статус 530: Принтер выключен или находится не в сети.')
        if not response.ok:
            raise RuntimeError(
                f'Статус {response.status}: {response.reason}')

    async def close(self):
        await self.session.close()
