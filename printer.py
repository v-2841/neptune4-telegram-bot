import os

from aiohttp import ClientSession


class PrinterAPI:
    def __init__(self):
        self.session = ClientSession(
            headers={
                'CF-Access-Client-Id': os.getenv('CLOUDFLARE_AC_ID', 'id'),
                'CF-Access-Client-Secret': os.getenv(
                    'CLOUDFLARE_AC_SECRET', 'secret')
            }
        )
        self.printer_url = os.getenv('PRINTER_URL', 'printer_url')

    async def server_config(self):
        async with self.session.get(
                self.printer_url + '/server/config') as response:
            return await response.json()

    async def printer_info(self):
        async with self.session.get(
                self.printer_url + '/printer/info') as response:
            return await response.json()

    async def proc_stats(self):
        async with self.session.get(
                self.printer_url + '/machine/proc_stats') as response:
            return await response.json()

    async def close(self):
        await self.session.close()
