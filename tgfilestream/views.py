import logging
import datetime

from aiohttp import web
import aiohttp_jinja2
from telethon.tl.custom import Message

from .util import unpack_id, get_file_name, get_requester_ip, get_human_size
from .config import request_limit
from .telegram import client, transfer


log = logging.getLogger(__name__)


class Views:
    

    async def index(self, req):
        raise web.HTTPFound('https://tx.me/tg2extbot')
    
    
    @aiohttp_jinja2.template('info.html')
    async def info(self, req):
        file_id = int(req.match_info["id"])
        peer, msg_id = unpack_id(file_id)
        if not peer or not msg_id:
            return {
                'found':False,
                'reason' : "File Not Found! Please Forward a file to our telegram bot to get a direct link!"
            }
        
        message = await client.get_messages(entity=peer, ids=msg_id)
        if not message:
            return {
                'found':False,
                'reason' : "File Not Found! Please Forward a file to our telegram bot to get a direct link!"
            }
        
        if (datetime.datetime.now(datetime.timezone.utc) - message.date).hours > 48:
            return {
                'found':False,
                'reason' : "Link Expired! Please Forward a file to our telegram bot to get a direct link!"
            }
        
        file_name = get_file_name(message)
        file_size = get_human_size(message.file.size)
        media = {
            'type':message.file.mime_type
        }
        if 'video/' in message.file.mime_type:
            media['video'] = True
        elif 'audio/' in message.file.mime_type:
            media['audio'] = True
        elif 'image/' in message.file.mime_type:
            media['image'] = True
            
        if message.text:
            caption = message.raw_text
        else:
            caption = False
        
        return {
            'found':True,
            'name':file_name,
            'id':file_id,
            'size':file_size,
            'media':media,
            'caption':caption
        }
    
    
    async def download_get(self, req):
        return await self.handle_request(req)
    
    
    async def download_head(self, req):
        return await self.handle_request(req, head=True)
    
    
    async def stream_file(self, req):
        return await self.handle_request(req, stream=True)
        
    
    
    async def handle_request(self, req, head=False, stream=False):
        file_id = int(req.match_info["id"])
        file_name = req.match_info["name"]
        peer, msg_id = unpack_id(file_id)
        if not peer or not msg_id:
            return web.Response(status=404, text="404: Not Found")

        message = await client.get_messages(entity=peer, ids=msg_id)
        if not message or not message.file:
            return web.Response(status=410, text="410: Gone. Access to the target resource is no longer available!")
        
        if get_file_name(message) != file_name:
            return web.Response(status=404, text="404: Not Found")
        
        if (datetime.datetime.now(datetime.timezone.utc) - message.date).hours > 48:
            return web.Response(status=410, text="410: Gone. Access to the target resource is no longer available!")

        size = message.file.size
        offset = req.http_range.start or 0
        limit = req.http_range.stop or size
        
        if (limit > size) or (offset < 0) or (limit < offset):
            return web.Response(
                status=416,
                text="416: Range Not Satisfiable",
                headers = {
                    "Content-Range": f"bytes */{size}"
                }
            )

        if not head:
            ip = get_requester_ip(req)
            log.info(f"Serving file in {message.id} (chat {message.chat_id}) to {ip}")
            body = transfer.download(message.media, file_size=size, offset=offset, limit=limit)
        else:
            body = None
        
        headers = {
            "Content-Type": message.file.mime_type,
            "Content-Range": f"bytes {offset}-{size}/{size}",
            #"Content-Length": str(limit - offset),
            "Accept-Ranges": "bytes"
        }
        
        if stream:
            headers["Content-Disposition"] = f'inline; filename="{file_name}"'
        else:
            headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
        
        resp = web.Response(
            status=206 if offset else 200,
            body=body,
            headers=headers
        )
        
        resp.enable_chunked_encoding()
        
        return resp
