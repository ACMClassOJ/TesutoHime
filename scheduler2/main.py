__import__('scheduler2.logging_')

from asyncio import new_event_loop
from atexit import register
from logging import getLogger

from aiohttp.web import AppRunner, Application, TCPSite

from scheduler2.config import listen
from scheduler2.rpc.runner.server import app as app_runner
from scheduler2.rpc.web.server import app as app_web

logger = getLogger(__name__)

# https://stackoverflow.com/a/59018487/13085717
def main():
    app_runners = []

    async def start_site(app: Application, host: str, port: int):
        runner = AppRunner(app)
        app_runners.append(runner)
        await runner.setup()
        site = TCPSite(runner, host, port)
        await site.start()

    loop = new_event_loop()
    loop.create_task(start_site(app_web, listen.web.host, listen.web.port))
    loop.create_task(start_site(app_runner, listen.runner.host, listen.runner.port))

    try:
        loop.run_forever()
    except:
        pass
    finally:
        for runner in app_runners:
            loop.run_until_complete(runner.cleanup())


if __name__ == '__main__':
    logger.info('scheduler starting', {}, 'scheduler:start')
    register(lambda: logger.info('scheduler stopping', {}, 'scheduler:stop'))
    main()
