# tgfilestream - A Telegram bot that can stream Telegram files to users over HTTP.
# Copyright (C) 2019 Tulir Asokan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from typing import Dict, cast
from collections import defaultdict
import logging

from aiohttp import web

from .util import get_file_name, get_requester_ip
from .config import channel_id
from .telegram import client, transfer

log = logging.getLogger(__name__)
routes = web.RouteTableDef()
ongoing_requests: Dict[str, int] = defaultdict(lambda: 0)


@routes.head(r"/get/{msg_id:\d+}")
async def handle_head_request(req: web.Request) -> web.Response:
    return await handle_request(req, head=True)


@routes.get(r"/get/{msg_id:\d+}")
async def handle_get_request(req: web.Request) -> web.Response:
    return await handle_request(req, head=False)


@routes.get("/")
async def handle_home_request(req: web.Request) -> web.Response:
    return web.Response(text="Hello There!")


async def handle_request(req: web.Request, head: bool = False) -> web.Response:
    msg_id = int(req.match_info["msg_id"])

    message = await client.get_messages(channel_id, ids=msg_id)
    if not message:
        return web.Response(status=404, text="404: Not Found")
    
    file_name = get_file_name(message)
    size = message.file.size
    offset = req.http_range.start or 0
    limit = req.http_range.stop or size

    if not head:
        ip = get_requester_ip(req)
        log.info(f"Serving file in {message.id} (chat {message.chat_id}) to {ip}")
        body = transfer.download(message.media, file_size=size, offset=offset, limit=limit)
    else:
        body = None
    return web.Response(status=206 if offset else 200,
                        body=body,
                        headers={
                            "Content-Type": message.file.mime_type,
                            "Content-Range": f"bytes {offset}-{size}/{size}",
                            "Content-Length": str(limit - offset),
                            "Content-Disposition": f'attachment; filename="{file_name}"',
                            "Accept-Ranges": "bytes",
                        })
