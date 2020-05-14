import asyncio
import pathlib
import sys

import aiohttp_jinja2
import jinja2
from aiohttp import web
from telethon import functions

from .telegram import client, transfer
from .routes import setup_routes
from .views import Views
from .config import host, port, public_url, bot_token
from .log import log

TEMPLATES_ROOT = pathlib.Path(__file__).parent / 'templates'


def setup_jinja(app):
    loader = jinja2.FileSystemLoader(str(TEMPLATES_ROOT))
    aiohttp_jinja2.setup(app, loader=loader)


async def start():
    await client.start(bot_token = bot_token)

    config = await client(functions.help.GetConfigRequest())
    for option in config.dc_options:
        if option.ip_address == client.session.server_address:
            if client.session.dc_id != option.id:
                log.warning(f"Fixed DC ID in session from {client.session.dc_id} to {option.id}")
            client.session.set_dc(option.id, option.ip_address, option.port)
            client.session.save()
            break
    transfer.post_init()


async def stop(app):
    await client.disconnect()


async def init(loop):
    server = web.Application()
    await start()
    setup_routes(server, Views())
    setup_jinja(server)
    server.on_cleanup.append(stop)
    return server


def main():
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init(loop))
    web.run_app(app, host=host, port=port)


if __name__ == '__main__':
    main()
